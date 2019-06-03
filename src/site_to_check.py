import attr


@attr.s
class SiteToCheck(object):
    jira_issue_key = attr.ib(validator=attr.validators.instance_of(str), default='')
    site_name = attr.ib(validator=attr.validators.instance_of(str), default='')
    persons_in_charge = attr.ib(validator=attr.validators.instance_of(list), default=attr.Factory(list))
    associated_unit = attr.ib(validator=attr.validators.instance_of(str), default='')
    jahia_url = attr.ib(validator=attr.validators.instance_of(str), default='')
    wordpress_url = attr.ib(validator=attr.validators.instance_of(str), default='')
    link_to_persons_having_editor_right = attr.ib(validator=attr.validators.instance_of(str), default='')
    link_to_accreditors_for_the_unit = attr.ib(validator=attr.validators.instance_of(str), default='')


