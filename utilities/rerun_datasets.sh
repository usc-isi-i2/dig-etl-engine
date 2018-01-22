dataset_path="/Users/amandeep/Github/sage-research-tool/datasets"
dig_tabular_path="/Users/amandeep/Github/dig-etl-engine/utilities/data_import"

# run usgold
usgold_path=$dataset_path/usgold
python $dig_tabular_path/dig_tabular_import.py $usgold_path/example/LBMA-GOLD.csv $usgold_path/goldprice_mapping.json $usgold_path/example/goldPrice_diginput.jl


python $dig_tabular_path/generate_mydig_config.py $usgold_path/goldprice_mapping.json $usgold_path