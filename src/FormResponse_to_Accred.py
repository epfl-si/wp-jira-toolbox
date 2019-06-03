import pandas as pb
import csv
from FormSubmission import FormSubmission
from accred_to_load import AccredToLoad


def get_data() -> list:
    return_value = list()

    base_data = pb.read_csv('../Vérification des accréditations (réponses) - 1 - Ajout des droits.csv')

    for index, data in base_data.iterrows():
        current_value = FormSubmission()
        current_value.site_name = data['Nom du site / site name']
        current_value.associated_unit = data['Unité associée au site / Associated Unit']

        separator = ''
        if data['Email(s) du (des) webmestre(s) de ce site / email(s) of the webmaster(s)'].find('|') > -1:
            separator = '|'
        elif data['Email(s) du (des) webmestre(s) de ce site / email(s) of the webmaster(s)'].find('\\') > -1:
            separator = '\\'
        elif data['Email(s) du (des) webmestre(s) de ce site / email(s) of the webmaster(s)'].find('/') > -1:
            separator = '/'
        elif data['Email(s) du (des) webmestre(s) de ce site / email(s) of the webmaster(s)'].find(',') > -1:
            separator = ','
        elif data['Email(s) du (des) webmestre(s) de ce site / email(s) of the webmaster(s)'].find(';') > -1:
            separator = ';'

        if separator == '':
            current_value.persons_in_charge.append(data['Email(s) du (des) webmestre(s) de ce site / email(s) of the webmaster(s)'].strip())
        else:
            for webmaster in data['Email(s) du (des) webmestre(s) de ce site / email(s) of the webmaster(s)'] \
                    .split(separator):
                current_value.persons_in_charge.append(webmaster.strip())

        return_value.append(current_value)

    return return_value


if __name__ == '__main__':
    data = get_data()
    AccredsToLoad = list()

    for item in data:
        for webmaster in item.persons_in_charge:
            current_value = AccredToLoad()
            current_value.unit = item.associated_unit
            current_value.email = webmaster
            current_value.right = 'WordPress Editor'
            AccredsToLoad.append(current_value)

    with open('rights_to_load.csv', 'w', newline='') as csvfile:
        entryWriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        for AccredToLoad in AccredsToLoad:
            entryWriter.writerow([AccredToLoad.email, AccredToLoad.unit, AccredToLoad.right])

