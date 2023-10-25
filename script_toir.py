import csv
from argparse import ArgumentParser
from datetime import datetime, timedelta
from os import getcwd
from os.path import join
from xml.etree.ElementTree import parse

import yaml
from xlsxwriter import Workbook

from tqdm import tqdm

from logic.xml_tools import get_text_value, get_date_value


def save(sheets, filename):
    wb = Workbook(filename)

    for sheet, data in sheets.items():
        ordered_list = [key for key in data[0].keys()]
        ws = wb.add_worksheet(sheet) # Or leave it blank. The default name is "Sheet 1"

        for header in ordered_list:
            col = ordered_list.index(header) # We are keeping order.
            ws.write(0, col, header) # We have written first row which is the header of worksheet also.

        for row_number, row in enumerate(data):
            for _key, _value in row.items():
                col = ordered_list.index(_key)
                ws.write(row_number + 1, col, _value)
    wb.close()

def translate_deptid(deptid):
    return f'{deptid[:3]}{str(hex(int(deptid[3:])))[-1].upper()}'


def translate_back_deptid(deptid):
    if deptid is None:
        return None
    return f'{deptid[:3]}{str(int(deptid[-1],16)).zfill(2)}'


def read_toir_from_file(xml_file):
    tree = parse(xml_file)
    root = tree.getroot()

    # читаем все фреймы в исходном файле
    rows = root.findall('Rows')

    report = [{
        'ID': get_text_value(equipment, "ID"),
        'EQUIPMENT_ID': get_text_value(equipment, "EQUIPMENT_ID"),
        'DEPT_ID': get_text_value(equipment, "DEPT_ID"),
        'MODEL': get_text_value(equipment, "MODEL"),
        'EQUIPMENT_GROUP_ID': get_text_value(equipment, "EQUIPMENT_GROUP_ID"),
        'EQUIPMENT_GROUP_NAME': get_text_value(equipment, "EQUIPMENT_GROUP_NAME"),
        'USAGE': get_text_value(equipment, "USAGE"),
        'REPAIR_TIME': get_text_value(equipment, "REPAIR_TIME"),
        'DATE_FROM': get_date_value(equipment, "DATE_FROM"),
        'DATE_TO': get_date_value(equipment, "DATE_TO"),
    } for equipment in tqdm(rows, desc='Считываем XML')]

    return report


def main():
    from logic import read_from_ftp

    parser = ArgumentParser(
        description='Инструмент консольной генерации отчетов '
                    'по результатам моделирования.'
    )

    parser.add_argument('-c', '--config', required=False,
                        default=join(getcwd(), 'kk_toir_parser.yml'))
    parser.add_argument('-s', '--server', required=False,
                        default=join(getcwd(), 'server.yml'))
    parser.add_argument('-r', '--repair_list', required=False,
                        default=join(getcwd(), 'repair_list.yml'))
    args = parser.parse_args()

    with open(args.repair_list, 'r', encoding="utf-8") as stream:
        repair_list = yaml.load(stream, Loader=yaml.SafeLoader)
    with open(args.server, 'r', encoding="utf-8") as stream:
        server = yaml.load(stream, Loader=yaml.SafeLoader)
    with open(args.config, 'r', encoding="utf-8") as stream:
        config = yaml.load(stream, Loader=yaml.SafeLoader)

    sftpURL = server['sftpURL']
    sftpUser = server['sftpUser']
    sftpPass = server['sftpPass']
    sftpPath = config['path']

    toir_data = read_from_ftp.read_toir_from_ftp(
        sftpURL, sftpUser, sftpPass, sftpPath
    )

    if 'use_groups' not in config:
        config['use_groups'] = True
    if not(config.get('use_groups')):
        for row in toir_data:
            row['EQUIPMENT_ID'], row['EQUIPMENT_GROUP_ID'] = row['EQUIPMENT_GROUP_ID'], ''

    equipment = []

    keys = toir_data[0].keys()

    with open('equipment_toir.csv', 'w', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(toir_data)

    repair_time = {}
    equipment_department = {}
    equipment_class = {}
    for row in toir_data:
        equipment_class[row['ID']] = row['EQUIPMENT_ID']
        equipment_department[row['ID']] = translate_deptid(row['DEPT_ID'])
        if row['USAGE'] != 'В ремонте':
            if row['ID'] in repair_list['repair_list']:
                del repair_list['repair_list'][row['ID']]
            continue
        repair_time[row['ID']] = int(row['REPAIR_TIME'].split()[0])
        if row['ID'] not in repair_list['repair_list']:
            repair_list['repair_list'][row['ID']] = datetime.now().replace(
                hour=0, minute=0, second=0
            )

    with open(args.repair_list, 'w') as output_file:
        yaml.dump(repair_list, output_file)

    unavailability = [
        {
            'DATE_FROM': f"{date_from.strftime('%Y-%m-%d %H:%M:%S')}+04:00",
            'DATE_TO': f"{(date_from + timedelta(days=repair_time[equipment])).strftime('%Y-%m-%d %H:%M:%S')}+04:00",
            'DEPARTMENT_ID': equipment_department[equipment],
            'EQUIPMENT_CLASS_ID': equipment_class[equipment],
            'EQUIPMENT_ID': equipment
        } for equipment, date_from in repair_list['repair_list'].items()
    ]

    for row in toir_data:
        if (row['DATE_FROM'] is None) or (row['DATE_TO'] is None):
            continue
        if row['DATE_FROM'] == row['DATE_TO']:
            continue
        unavailability.append({
            'DATE_FROM': f"{row['DATE_FROM'].strftime('%Y-%m-%d %H:%M:%S')}+04:00",
            'DATE_TO': f"{row['DATE_TO'].strftime('%Y-%m-%d %H:%M:%S')}+04:00",
            'DEPARTMENT_ID': equipment_department[row['ID']],
            'EQUIPMENT_CLASS_ID': equipment_class[row['ID']],
            'EQUIPMENT_ID': row['ID']
        })

    save(
        {
            'equipment_unavailability': unavailability,
        },
        'equipment_change.xlsx'
    )


if __name__ == '__main__':
    main()
