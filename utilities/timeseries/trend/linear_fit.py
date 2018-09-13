import trend_analysis as ta
import logging
import numpy as np
from pwlf import pwlf
from sets import Set
import time

class linear_fit:
    anomaly_threshold = 0.4
    description_words = ["decreasing - quickly", "decreasing", "decreasing - slowly", "flat",
                         "increasing - slowly", "increasing", "increasing - quickly"]
    description_thresholds = [-2, -0.5, -0.05, 0.05, 0.5, 2]
    error_step_hyper_param = 0.02 # the cost of adding one more line to best number of lines
    y_axis_scale = 50 # the scale of the y-axis after removing anomaly points. This scale is used in describing the linear fits tangents
    x_axis_scale = 1 # should we scale the time-axis?
    num_iteration = 0 # number of iteration to find the best linear fit among those found
    epsilon = 0.0001

    def __init__(self):
        self.initial = 0
    # based on the value of the tangent of the line describes its behaviour. Note that the value of slope is scaled and it's not the real value

    # a better version
    def analyze_series_with_points(self, series):
        try:
            if len(series.values) > 0 and max(series.values) != min(series.values):
                self.y_axis_scale = 1.0 * (max(series.times) - min(series.times)) / (
                max(series.values) - min(series.values))
            if len(series.times) <= 6:
                return {"linear fits": self.linear_fit_for_small_data(series), 'anomaly points': []}

        # find anomaly points and remove them
            series_copy = ta.time_series(times=series.times, time_labels=series.times_labels, values=series.values)
            out_json = {'linear fits': [], 'anomaly points': [self.remove_anomalies(series_copy)]}
            anomaly_free_series = ta.time_series(times=np.array([i for i in series_copy.times]),values=np.array(series_copy.values), time_labels=series_copy.times_labels)

        ###----------------- the case that there are a lot of anomalies which happens like "|\|\|\--------------------"
            if (len(anomaly_free_series.times) < 5):
                out_json['linear fits'] = self.linear_fit_for_small_data(anomaly_free_series)
                return out_json


            break_points = Set([])
            num_lines, res, best_linear_fit = self.estimate_number_of_lines(anomaly_free_series.times, anomaly_free_series.values)
            break_points = break_points.union(self.find_fitted_lines_break_points(series, res))
            for i in range(self.num_iteration):
                num_lines, res, best_linear_fit = self.estimate_number_of_lines(anomaly_free_series.times, anomaly_free_series.values)
                break_points = break_points.union(self.find_fitted_lines_break_points(series, res))

            points = [min(series.times), max(series.times)]
            for x in break_points:
                if x > 0 and x < len(series.times)-1:
                    points.append(series.times[x] + self.epsilon)


            # res = best_linear_fit.fitWithBreaks(np.array(sorted(points))) # this line is necessary although it seems useless

        # writing the description for the piecewise linear
            out_json['linear fits'] = self.create_output_Intervals(anomaly_free_series, series, best_linear_fit, sorted(points))

        # this part is only for plotting
        #     xHat = np.linspace(min(series.times), max(series.times), num=100)
        #     yHat = best_linear_fit.predict(xHat)
            return out_json
        except:

            return [{"start":0, "end":0, "description":"Problem Occured", "meta_data":{}}]
    def analyze_series(self, series):
        # try:
            # check the size of series to be more than 4 other wise return
            if len(series.times) <= 5:
                return {"linear fits":self.linear_fit_for_small_data(series), 'anomaly points':[]}

            # find anomaly points and remove them
            series_copy = ta.time_series(times=series.times, time_labels=series.times_labels, values=series.values)
            out_json = {'linear fits': [], 'anomaly points': [self.remove_anomalies(series_copy)]}
            anomaly_free_series = ta.time_series(times=np.array([i for i in series_copy.times]), values=np.array(series_copy.values), time_labels=series_copy.times_labels)

            ###----------------- the case that there are a lot of anomalies which happens like "|\|\|\--------------------"
            if (len(anomaly_free_series.times) < 4):
                out_json['linear fits'] = self.linear_fit_for_small_data(anomaly_free_series)
                return out_json

            num_lines, res, best_linear_fit = self.estimate_number_of_lines(anomaly_free_series.times, anomaly_free_series.values) # hyper parameter assumed to be 0.005

            # writing the description for the piecewise linear
            out_json['linear fits'] = self.create_output_Intervals(anomaly_free_series, series, best_linear_fit, res)

            # this part is only for plotting
            xHat = np.linspace(min(series.times), max(series.times), num=100)
            yHat = best_linear_fit.predict(xHat)
            return out_json, xHat, yHat
        # except:
        #     # maybe here I should return an exception or message
        #     logging.error("somethinig happened in linear fit for this series: " + str(series))
        #     return None

    # finds the lines connecting the points in data. It's for the case that the length of series is small
    def linear_fit_for_small_data(self, series):
        out_json = []
        if len(series.times) == 1:
            return [{"start":series.times_labels[0], "end":series.times_labels[0], "description":"single_point", "meta_data":{}}]
        for i in range(len(series.times) - 1):
            slope = self.y_axis_scale *(series.values[i + 1] - series.values[i]) / (series.times[i + 1] - series.times[i])
            meta_data = {"slope":slope, "intercept": series.values[i] - slope * series.times[i]}
            out_json.append({"start":series.times_labels[i], "end":series.times_labels[i+1], "description":  self.describe_slope(slope), "meta_data":meta_data})
        return out_json

    # find the anomaly points.
    # The anomaly points here are the points in series that are very different from their both neighbors and change the predicted linear fits
    def find_anomaly(self, series):
        if (len(series.times) <= 8): # it does not makes sense to have anomaly in a small sample of times
            return []

        anomaly_values = []
        anomaly_indices = []

        # get the distance of the point from it's nearest neighbor
        for i in range(len(series.values)):
            if i - 1 >= 0 and i+1 < len(series.values):
                tmp = min(abs(series.values[i] - series.values[i-1]), abs(series.values[i] - series.values[i+1]))
                anomaly_values.append(tmp)
            elif i - 1 < 0:
                anomaly_values.append(abs(series.values[i] - series.values[i+1]))
            else:
                anomaly_values.append(abs(series.values[i] - series.values[i-1]))

        # check for the high left and right derivative of each candidate since we are only intersted in anomalies like ...../\.....
        for i in range(len(anomaly_values)):
            if anomaly_values[i] > (max(series.values) - min(series.values))* self.anomaly_threshold:
                if i == 0 or i == len(series.values) - 1:
                    logging.info("anomaly detected at the beginning or end of interval! check it in all cases")
                    anomaly_indices.append(i)
                elif (series.values[i]-series.values[i-1])*(series.values[i+1]-series.values[i]) < 0:
                        anomaly_indices.append(i)
        return anomaly_indices

    # find and remove anomalies in the time sesries
    def remove_anomalies(self, series):
        anomalies = self.find_anomaly(series)
        anomaly_labels = []
        for i in reversed(anomalies):
            anomaly_labels.append(series.times_labels.pop(i))
            series.values.pop(i)
            series.times.pop(i)
        return anomaly_labels

    # find the appropriate number of lines and the best linear fit:
    def estimate_number_of_lines(self, x, y):
        # starting from 1 line and adding and comparing the errors:
        prevError = float('Inf')
        e, tmp_pwlf, tmp_fit = self.compute_linear_error(3, x, y)
        for i in range(max(1, (len(x)/ 3))):
            error, curr_pwlf, fit = self.compute_linear_error(i + 3, x, y)
            estimated_cost = error / len(x) + self.error_step_hyper_param * (i + 3)
            logging.info('linear error ' + str(error / len(x)))
            logging.info('estimated cost with ' + str(i + 3) + ' lines is: ' + str(estimated_cost))
            if estimated_cost > prevError:
                return i + 3, fit, curr_pwlf
            prevError = estimated_cost
            tmp_fit = fit
            tmp_pwlf = curr_pwlf
        e, tmp_pwlf, tmp_fit = self.compute_linear_error(len(x)/3, x, y)
        return len(x)/3, tmp_fit, tmp_pwlf

    # given the number of lines, it computes the piecewise linear fit with the specified number of lines. Also computes the sqaured error of the piecewise fit
    def compute_linear_error(self, num_lines, x, y):  # if number of lines is 1 or 2 try to find another solution
        Linear_error = 0
        myPWLF = pwlf.piecewise_lin_fit(x, y)
        res = myPWLF.fit(num_lines) # this line is necessary although it seems useless
        for i in range(len(x)):
            xi = x[i]
            yH = myPWLF.predict(xi)
            Linear_error += (yH - y[i]) * (yH - y[i])
        return Linear_error/ (max(y)-min(y))** 2, myPWLF, res

    # describe the features of a fitted line in an interval. The features are slope of linear regression, intercept of the line and description
    def describe_fitted_line(self, x_start, x_end, pwlf, y_magnitude):
        y_end = pwlf.predict(x_end)
        y_start = pwlf.predict(x_start)
        slope = (y_end - y_start) * y_magnitude / (x_end - x_start)
        return slope, y_start - slope * x_start, self.describe_slope(slope)

    # based on the value of tangent of line assing a description to it
    def describe_slope(self, slope_val):
        for i in range(len(self.description_thresholds)):
            if slope_val < self.description_thresholds[i]:
                return self.description_words[i]
        return self.description_words[-1]

    # creates the output dictionary for the given fitted lines
    # needs some improvement for small data set
    def create_output_Intervals(self, refined_series, original_series, best_linear_fit, fitted_lines):
        Interval_descriptoins = []
        last_visited_interval_ind = 0
        slope, intercept, description = self.describe_fitted_line(fitted_lines[0], fitted_lines[1],best_linear_fit, (self.y_axis_scale / (max(refined_series.values) - min(refined_series.values))))
        Interval_descriptoins.append({"start": original_series.times_labels[last_visited_interval_ind], "description": description,"meta_data": {"slope": slope[0], "intercept": intercept[0]}})

        for i in range(len(fitted_lines) - 2):
            slope, intercept, description = self.describe_fitted_line(fitted_lines[i+1], fitted_lines[i + 2], best_linear_fit, (self.y_axis_scale / (max(refined_series.values) - min(refined_series.values))))
            # search the values in x_copy then find the string in labels
            for j in range(len(original_series.times) - 1):
                if fitted_lines[i+1]-self.epsilon == original_series.times[j+1] :
                    last_visited_interval_ind = j+1
            Interval_descriptoins.append({"start":original_series.times_labels[last_visited_interval_ind], "description":description, "meta_data":{"slope":slope[0], "intercept":intercept[0]}})
        # the end of each interval is the start of another interval
        for i in range(len(Interval_descriptoins)-1):
            Interval_descriptoins[i]["end"] = Interval_descriptoins[i+1]["start"]
        Interval_descriptoins[len(Interval_descriptoins)-1]["end"] = original_series.times_labels[-1]
        return Interval_descriptoins


    # given an estimate of break points find the closest point in our time series to these points
    def find_fitted_lines_break_points(self, original_series, fitted_lines):
        last_visited_interval_ind = 0
        break_points = Set([])
        for i in range(len(fitted_lines) - 2):
            for j in range(len(original_series.times) - 1):
                d1 = fitted_lines[i+1] - original_series.times[j]
                d2 = original_series.times[j+1] - fitted_lines[i+1]
                if d1 > 0 and d2 > 0:
                    if d1 < d2:
                        last_visited_interval_ind = j
                    else:
                        last_visited_interval_ind = j+1

            break_points.add(last_visited_interval_ind)
        return break_points