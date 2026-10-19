"""Task032 authorized resume: one GRS instance, fresh manifest and run folder."""
import run as base

base.MANIFEST = base.HERE / 'inputs_grs_resume.json'
base.TAG = 'ds_data_bus_response_turnover_grs_resume_20261014_a'


if __name__ == '__main__':
    base.main()
