import attr


@attr.s
class FormSubmission(object):
    site_name = attr.ib(validator=attr.validators.instance_of(str), default='')
    persons_in_charge = attr.ib(validator=attr.validators.instance_of(list), default=attr.Factory(list))
    associated_unit = attr.ib(validator=attr.validators.instance_of(str), default='')
