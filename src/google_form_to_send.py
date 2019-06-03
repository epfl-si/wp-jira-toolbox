import attr


@attr.s
class GoogleFormToSend(object):
    site = attr.ib(validator=attr.validators.instance_of(str), default='')
    jahia_url = attr.ib(validator=attr.validators.instance_of(str), default='')
    associated_unit = attr.ib(validator=attr.validators.instance_of(str), default='')
    webmasters = attr.ib(validator=attr.validators.instance_of(str), default='')
    google_form_url = attr.ib(validator=attr.validators.instance_of(str), default='')


