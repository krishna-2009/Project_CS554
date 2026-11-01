.PHONY: reproduce checkin herd cds reference package

reproduce:
	python3 scripts/run_experiments.py --graphs --pdf

checkin:
	python3 scripts/run_experiments.py --tables-only --pdf

herd:
	python3 scripts/run_herd.py --graphs

cds:
	python3 scripts/run_cds.py

reference:
	python3 scripts/reference_checker.py

package:
	python3 scripts/package_project.py
