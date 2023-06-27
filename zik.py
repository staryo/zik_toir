import argparse
import csv
from argparse import ArgumentParser
from collections import defaultdict
from glob import glob
from os import getcwd, path
from os.path import join

import yaml

import save_to_excel
from translate_deptid import translate_deptid
from version_zik import DESCRIPTION


def main():

    parser = ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=DESCRIPTION
    )

    parser.add_argument('-c', '--config', required=False,
                        default=join(getcwd(), 'config.yml'))
    parser.add_argument('-t', '--time_tables', required=False,
                        default=join(getcwd(), 'time_tables.yml'))

    args = parser.parse_args()

    with open(args.config, 'r', encoding="utf-8") as stream:
        config = yaml.load(stream, Loader=yaml.SafeLoader)
    with open(args.time_tables, 'r', encoding="utf-8") as stream:
        time_table = yaml.load(stream, Loader=yaml.SafeLoader)

    list_of_files = glob(f'{config["path"]}/{config["pattern"]}*')
    latest_file = max(list_of_files, key=path.getctime)
    print(latest_file)
    dept_schedule = defaultdict(lambda: defaultdict(int))
    set_of_shifts = set(
        [
            f'{time_table["time_tables"][schedule]["table"]}_'
            f'{time_table["time_tables"][schedule]["shift"]}'
            for schedule in time_table['time_tables']
        ]
    )
    dept_total = defaultdict(int)

    with open(latest_file, 'r') as input_file:
        data = csv.DictReader(input_file)
        for row in data:
            table = time_table['time_tables'][row['SCHEDULE_ID']]['table']
            shift = time_table['time_tables'][row['SCHEDULE_ID']]['shift']
            dept_id = translate_deptid(row['DEPT_ID'])
            dept_schedule[dept_id][f'{table}_{shift}'] += 1
            # set_of_shifts.add(f'{table}_{shift}')
            dept_total[dept_id] += 1

    employee_variation = [{
        'SCHEDULE_ID': time_table['default_time_table'],
        'ECONOMIC_INVESTMENTS': 0,
        'ECONOMIC_COST': 0
    }]

    profession_time_table = [
        {
            'PROFESSION_ID': f'{dept}_worker',
            'DEPARTMENT_ID': dept,
            'TIME_TABLE_ID': shift,
            'AMOUNT': schedule_data[shift]
        } for dept, schedule_data in dept_schedule.items()
        for shift in set_of_shifts
    ]

    save_to_excel.save(
        {
            'employee_variation': employee_variation,
            # 'department_schedule': department_schedule,
            'profession_time_table': profession_time_table
        },
        'prof_change.xlsx'
    )

    prof_total = [
        {
            'ID': f'{dept}_worker',
            'DEPT_ID': dept,
            'NAME': f'Рабочий участка {dept}',
            'AMOUNT': amount
        } for dept, amount in dept_total.items()
    ]

    save_to_excel.save(
        {
            'prof': prof_total,
        },
        'prof.xlsx'
    )


if __name__ == "__main__":
    main()