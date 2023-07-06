import csv
from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime, timedelta
from os import getcwd
from os.path import join
from xml.etree.ElementTree import parse

import yaml
from xlsxwriter import Workbook

from tqdm import tqdm

from logic.xml_tools import get_text_value


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


def read_zik_from_file(xml_file):
    tree = parse(xml_file)
    root = tree.getroot()

    # читаем все фреймы в исходном файле
    rows = root.findall('Rows')

    report = [{
        'PROF_ID': get_text_value(row, "PROF_ID"),
        'DEPT_ID': get_text_value(row, "DEPT_ID"),
        'NAME': get_text_value(row, "NAME"),
        'NAME_ID': get_text_value(row, "NAME_ID"),
        'SCHEDULE_ID': get_text_value(row, "SCHEDULE_ID"),
    } for row in tqdm(rows, desc='Считываем XML')]

    return report


def main():
    from logic import read_from_ftp

    parser = ArgumentParser(
        description='Инструмент консольной генерации отчетов '
                    'по результатам моделирования.'
    )

    parser.add_argument('-c', '--config', required=False,
                        default=join(getcwd(), 'kk_zik_parser.yml'))
    parser.add_argument('-s', '--server', required=False,
                        default=join(getcwd(), 'server.yml'))
    parser.add_argument('-t', '--time_tables', required=False,
                        default=join(getcwd(), 'time_tables.yml'))
    args = parser.parse_args()

    with open(args.time_tables, 'r', encoding="utf-8") as stream:
        time_table = yaml.load(stream, Loader=yaml.SafeLoader)
    with open(args.server, 'r', encoding="utf-8") as stream:
        server = yaml.load(stream, Loader=yaml.SafeLoader)
    with open(args.config, 'r', encoding="utf-8") as stream:
        config = yaml.load(stream, Loader=yaml.SafeLoader)

    sftpURL = server['sftpURL']
    sftpUser = server['sftpUser']
    sftpPass = server['sftpPass']
    sftpPath = config['path']

    data = read_from_ftp.read_zik_from_ftp(
        sftpURL, sftpUser, sftpPass, sftpPath
    )

    dept_schedule = defaultdict(lambda: defaultdict(int))
    set_of_shifts = set(
        [
            f'{time_table["time_tables"][schedule]["table"]}_'
            f'{time_table["time_tables"][schedule]["shift"]}'
            for schedule in time_table['time_tables']
        ]
    )
    dept_total = defaultdict(int)

    for row in data:
        table = time_table['time_tables'][row['SCHEDULE_ID']]['table']
        shift = time_table['time_tables'][row['SCHEDULE_ID']]['shift']
        dept_id = translate_deptid(row['DEPT_ID'])
        if dept_id in config['change_department']:
           dept_id = config['change_department'][dept_id]
        # dept_schedule[dept_id][f'{table}_{shift}'] += 1
        # set_of_shifts.add(f'{table}_{shift}')
        if table == '10':
            dept_schedule[dept_id][f'{table}_{"01"}'] += 1
            dept_schedule[dept_id][f'{table}_{"02"}'] += 1
            dept_total[dept_id] += 2
        elif table == '11' and (shift == '01' or shift == '03'):
            dept_schedule[dept_id][f'{table}_{"01"}'] += 1
            dept_schedule[dept_id][f'{table}_{"03"}'] += 1
            dept_total[dept_id] += 2
        elif table == '11' and (shift == '02' or shift == '04'):
            dept_schedule[dept_id][f'{table}_{"02"}'] += 1
            dept_schedule[dept_id][f'{table}_{"04"}'] += 1
            dept_total[dept_id] += 2
        else:
            dept_schedule[dept_id][f'{table}_{shift}'] += 1
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

    save(
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

    save(
        {
            'prof': prof_total,
        },
        'prof.xlsx'
    )


if __name__ == '__main__':
    main()
