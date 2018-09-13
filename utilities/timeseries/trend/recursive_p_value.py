import trend_analysis as ta
import logging
import numpy as np
import pwlf
from sets import Set
import time
import matplotlib.pyplot as plt
import statsmodels.api as sm

from scipy import stats

class line:
    def __init__(self, slope, intercept):
        self.slope = slope
        self.intercept = intercept

class recursive_linear_fit:
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
    def pValue(self, X, Y, alphaOld, betaOld):
        n = len(X)
        Xc = sm.add_constant(X)
        line = sm.OLS(Y, Xc).fit()
        alpha, beta = line.params[0], line.params[1]

        yHat = line.predict(Xc)

        xBar = X.mean()
        yBar = Y.mean()
        Sxx = ((X - xBar) ** 2).sum()
        Sqx = (X ** 2).sum()
        Sxy = ((X - xBar) * (Y - yBar)).sum()
        Syy = ((Y - yBar) ** 2).sum()
        sigmaSq = ((Y - yHat) ** 2).sum()
        S = np.sqrt(sigmaSq / (n - 2))

        betaStat = abs((beta - betaOld) * np.sqrt(Sxx) / S)
        alphaStat = abs((alpha - alphaOld) / (S * np.sqrt(Sqx / (n * Sxx))))

        p_beta = stats.t.sf(betaStat, n - 2) * 2

        p_alpha = stats.t.sf(alphaStat, n - 2) * 2

        return alpha, beta, p_alpha, p_beta

    def compute_p_value(self, x, y, prev_slope, prev_intercept):
        alpha, beta, p_alpha, p_beta = self.pValue(np.array(x), np.array(y), prev_intercept, prev_slope)

        left_line = line(beta, alpha)

        return left_line, [p_alpha, p_beta]

    def find_linear_fit(self, x, x_labels, y, prev_slope, prev_intercept, line_seqments):
        # alpha is intercept
        logging.info("inside dividing line")
        logging.info(x_labels)
        division_point, lines = self.find_division_point(x, y, prev_slope, prev_intercept)
        if division_point == -1: # it must return the whole line and add it to line_seqments
            line_seqments.append([x_labels[0], x_labels[-1], prev_slope, prev_intercept, x[0], x[-1]])
            return
        logging.info("This is considered the division point in this step: ")
        logging.info(division_point)
        logging.info("[" + str(x_labels[0]) + " " + str(x_labels[-1]) + "] point is: " + str(x_labels[division_point]))

            # it should run for the right and left side
        self.find_linear_fit(x[0:division_point+1], x_labels[0:division_point+1],y[0:division_point+1], lines[0].slope, lines[0].intercept, line_seqments)
        self.find_linear_fit(x[division_point:], x_labels[division_point:],y[division_point:], lines[1].slope, lines[1].intercept, line_seqments)

    # threshold
    def find_division_point(self, x, y, prev_slope, prev_intercept):

        threshold = 0.1
        # first it has to compute L_m for each of the points in the series
        if len(x) <= 5:
            return -1, None
        candidates = []
        for i in range(len(x)-2):
            left_line, left_p = self.compute_p_value(x[0:i+2], y[0:i+2], prev_slope, prev_intercept)
            right_line, right_p = self.compute_p_value(x[i+1:], y[i+1:], prev_slope, prev_intercept)
            candidate = []
            logging.info("point: " + str(x[i])+"[left_pvalue: " + str(left_p) + "right_pvalue:"+ str(right_p)+"]")
            if left_p[0] > threshold or left_p[1] > threshold or right_p[0] > threshold or right_p[1] > threshold:
                continue # not a good point for being a division point

            candidate.append(min(self.L_function(left_p), self.L_function(right_p)))
            candidate.append(i+1)
            candidate.append([left_line, right_line])
            candidates.append(candidate)

        # find the minimum here now
        if len(candidates) == 0: # no candidate point with the confidence more than 95%
            return -1, None

        min_index = 0
        for i in range(len(candidates)):
            if candidates[i][0] < candidates[min_index][0]:
                min_index = i
        return candidates[min_index][1], candidates[min_index][2]
    def L_function(self, p_value):
        return p_value[0] + p_value[1]
    def analyze_series_with_points(self, series):
        # try:
            logging.info("Inside recursive Value computing")
            logging.info("series: ")
            logging.info(series.times)
            logging.info(series.values)
            # find anomaly points and remove them
            series_copy = ta.time_series(times=series.times, time_labels=series.times_labels, values=series.values)
            out_json = {'linear fits': [], 'anomaly points': [self.remove_anomalies(series_copy)]}
            # print out_json
            anomaly_free_series = ta.time_series(times=np.array([i for i in series_copy.times]),values=np.array(series_copy.values), time_labels=series_copy.times_labels)

            lines = []

            # find the first line here
            logging.info("before p value computation")
            first_line, dummy_p = self.compute_p_value(series.times, series.values, 1, 1)
            logging.info("first estimated_line: ")
            prev_slope = first_line.slope
            prev_intercept = first_line.intercept
            logging.info(str(prev_slope) + " , " + str(prev_intercept))

            self.find_linear_fit(series.times, series.times_labels, series.values, prev_slope, prev_intercept, lines)


            out_json['linear fits'] = self.create_output_Intervals(lines)

        # this part is only for plotting
            xHat = np.linspace(min(series.times), max(series.times), num=100)
            yHat = self.predict(xHat, lines)
            plt.plot(series.times, series.values)
            plt.plot(xHat, yHat)
            plt.show()

            # time.sleep()
            return out_json
        # except:
        #
        #     return [{"start":0, "end":0, "description":"Problem Occured", "meta_data":{}}]

    # finds the lines connecting the points in data. It's for the case that the length of series is small

    # find the anomaly points.
    # The anomaly points here are the points in series that are very different from their both neighbors and change the predicted linear fits
    def find_anomaly(self, series):
        if (len(series.times) <= 100): # it does not makes sense to have anomaly in a small sample of times
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

    def predict(self, x_array, lines):
        y = []
        for x in x_array:
            y.append(self.predict_y(x, lines))
        return y
    def predict_y(self, x, lines):
        for line in lines:
            if x >= line[4] and x <= line[5]:
                return line[2]*x + line[3]


    # find and remove anomalies in the time sesries
    def remove_anomalies(self, series):
        anomalies = self.find_anomaly(series)
        anomaly_labels = []
        for i in reversed(anomalies):
            anomaly_labels.append(series.times_labels.pop(i))
            series.values.pop(i)
            series.times.pop(i)
        return anomaly_labels

    # based on the value of tangent of line assing a description to it
    def describe_slope(self, slope_val):
        for i in range(len(self.description_thresholds)):
            if slope_val < self.description_thresholds[i]:
                return self.description_words[i]
        return self.description_words[-1]

    # creates the output dictionary for the given fitted lines
    # needs some improvement for small data set
    def create_output_Intervals(self, fitted_lines):
        Interval_descriptoins = []
        for line in fitted_lines:
            description = self.describe_slope(line[3])
            Interval_descriptoins.append({"start":line[0], "end":line[1], "description":description, "meta_data":{"slope":line[3], "intercept":line[4]}})

        return Interval_descriptoins
