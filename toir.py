import argparse
import csv
from argparse import ArgumentParser
from datetime import datetime, timedelta
from glob import glob
from os import getcwd, path
from os.path import join

import yaml

import save_to_excel
from translate_deptid import translate_deptid
from version_toir import DESCRIPTION


def main():

    parser = ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=DESCRIPTION
    )

    parser.add_argument('-c', '--config', required=False,
                        default=join(getcwd(), 'config_equipment.yml'))
    parser.add_argument('-r', '--repair_list', required=False,
                        default=join(getcwd(), 'repair_list.yml'))

    args = parser.parse_args()

    with open(args.config, 'r', encoding="utf-8") as stream:
        config = yaml.load(stream, Loader=yaml.SafeLoader)
    with open(args.repair_list, 'r', encoding="utf-8") as stream:
        repair_list = yaml.load(stream, Loader=yaml.SafeLoader)

    list_of_files = glob(f'{config["path"]}/{config["pattern"]}*')
    latest_file = max(list_of_files, key=path.getctime)
    print(latest_file)

    with open(latest_file, 'r', encoding='utf-8-sig') as input_file:
        data = csv.DictReader(input_file)
        toir_data = [
            {
                key: value for key, value in row.items()
            } for row in data
        ]
    if 'use_groups' not in config:
        config['use_groups'] = True
    if not(config.get('use_groups')):
        for row in toir_data:
            row['EQUIPMENT_ID'], row['EQUIPMENT_GROUP_ID'] = row['EQUIPMENT_GROUP_ID'], ''

    keys = toir_data[0].keys()

    with open('equipment_toir.csv', 'w', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(toir_data)

    repair_time = {}
    equipment_department = {}
    equipment_class = {}
    for row in toir_data:
        if row['USAGE'] != 'В ремонте':
            if row['ID'] in repair_list['repair_list']:
                del repair_list['repair_list'][row['ID']]
            continue
        equipment_class[row['ID']] = row['EQUIPMENT_ID']
        equipment_department[row['ID']] = translate_deptid(row['DEPT_ID'])
        repair_time[row['ID']] = int(row['REPAIR_TIME'].split()[0])
        if row['ID'] not in repair_list['repair_list']:
            repair_list['repair_list'][row['ID']] = datetime.now().replace(
                hour=0, minute=0, second=0
            )

    with open(args.repair_list, 'w') as output_file:
        yaml.dump(repair_list, output_file)

    unavailability = [
        {
            'DATE_FROM': date_from.strftime('%Y-%m-%d %H:%M:%S'),
            'DATE_TO': (
                    date_from + timedelta(days=repair_time[equipment])
            ).strftime('%Y-%m-%d %H:%M:%S'),
            'DEPARTMENT_ID': equipment_department[equipment],
            'EQUIPMENT_CLASS_ID': equipment_class[equipment],
            'EQUIPMENT_ID': equipment
        } for equipment, date_from in repair_list['repair_list'].items()
    ]

    save_to_excel.save(
        {
            'equipment_unavailability': unavailability,
        },
        'equipment_change.xlsx'
    )


if __name__ == "__main__":
    main()