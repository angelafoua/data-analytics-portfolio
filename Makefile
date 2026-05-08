.PHONY: all clean project1 project2 project3 data dashboards

PYTHON ?= python3

all: data dashboards

data:
	$(PYTHON) project_1_sales_analysis/scripts/generate_data.py
	$(PYTHON) project_2_customer_analytics/scripts/generate_data.py
	$(PYTHON) project_3_operations_analytics/scripts/generate_data.py

dashboards:
	$(PYTHON) project_1_sales_analysis/dashboard/build_dashboard.py
	$(PYTHON) project_2_customer_analytics/dashboard/build_dashboard.py
	$(PYTHON) project_3_operations_analytics/dashboard/build_dashboard.py

project1:
	$(PYTHON) project_1_sales_analysis/scripts/generate_data.py
	$(PYTHON) project_1_sales_analysis/dashboard/build_dashboard.py

project2:
	$(PYTHON) project_2_customer_analytics/scripts/generate_data.py
	$(PYTHON) project_2_customer_analytics/dashboard/build_dashboard.py

project3:
	$(PYTHON) project_3_operations_analytics/scripts/generate_data.py
	$(PYTHON) project_3_operations_analytics/dashboard/build_dashboard.py

clean:
	rm -f project_1_sales_analysis/data/*.csv
	rm -f project_2_customer_analytics/data/*.csv
	rm -f project_3_operations_analytics/data/*.csv
	rm -f project_1_sales_analysis/dashboard/*.html
	rm -f project_2_customer_analytics/dashboard/*.html
	rm -f project_3_operations_analytics/dashboard/*.html
