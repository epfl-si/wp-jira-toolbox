import re

import ldap3
from jira import JIRA
from ldap3 import ALL, Connection, Server

import settings


def get_list_of_units()->list:
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))
    sites = jira.search_issues("project = WPFEEDBACK and type=story", maxResults=1000)

    units = list()

    for site in sites:
        if site.fields.customfield_10404 != None and site.fields.customfield_10404 not in units:
            units.append(site.fields.customfield_10404)

    return units

def get_second_level_unit(unit:str)->str:
    level_2_unit = ''

    LDAP_server = Server(settings.LDAP_SERVER, use_ssl=True, get_info=ALL)
    conn = Connection(LDAP_server, auto_bind=True)
    conn.search(settings.LDAP_BASE_DN,
                '(&(objectClass=EPFLorganizationalUnit)(objectClass=posixGroup)(cn={}))'.format(unit),
                attributes=[],
                size_limit=1)
    if len(conn.entries) == 1:
        current_dn = conn.entries[0].entry_dn
        hierarchy = current_dn.split(',')
        if hierarchy[2]=='o=epfl':
            level_2_unit = hierarchy[1].split('=')[1]
        else:
            level_2_unit = hierarchy[2].split('=')[1]
        
        print("{:15} -> {:50} -> {}".format(unit, current_dn,level_2_unit))
    
    return level_2_unit

def get_second_level_units(units:list)->dict:
    return_value = dict()
    ldap_base_filter = '(&(objectClass=EPFLorganizationalUnit)(objectClass=posixGroup)(|{}))'
    ldap_unit_filter = ''
    for unit in units:
        ldap_unit_filter += '(cn={})'.format(unit)

    ldap_filter = ldap_base_filter.format(ldap_unit_filter)

    LDAP_server = Server(settings.LDAP_SERVER, use_ssl=True, get_info=ALL)
    conn = Connection(LDAP_server, auto_bind=True)
    conn.search(settings.LDAP_BASE_DN,
                ldap_filter,
                attributes='cn')

    for entry in conn.entries:
        current_dn = entry.entry_dn
        hierarchy = current_dn.split(',')
        if hierarchy[2]=='o=epfl':
            level_2_unit = hierarchy[1].split('=')[1]
        else:
            level_2_unit = hierarchy[2].split('=')[1]
        
        return_value[entry.cn.value] = level_2_unit
    
    return return_value

def update_jira(mapping:dict)->None:
    for key, value in mapping.items():
        print("{:15} -> {}".format(key,value))

        jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))
        sites = jira.search_issues("project = WPFEEDBACK and type=story AND 'Unit name' ~ '{}'".format(key), maxResults=1000)

        for site in sites:
            if site.fields.customfield_10404 == key:
                if site.fields.customfield_10700 != value:
                    # update unit level 2 (customfield_10700) unit with current value 
                    print("{} updating level 2 unit with '{}'".format(site.key, value))
                    site.update(fields={'customfield_10700': value})
                
                if site.fields.customfield_10404 != site.fields.customfield_10404.upper():
                    # update the associated unit with uppercase
                    print("{} updating associated unit with '{}'".format(site.key, site.fields.customfield_10404.upper()))
                    site.update(fields={'customfield_10404': site.fields.customfield_10404.upper()})

if __name__ == "__main__":
    units = get_list_of_units()

    mapping = get_second_level_units(units)

    update_jira(mapping)
