from xlsxwriter import Workbook


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
