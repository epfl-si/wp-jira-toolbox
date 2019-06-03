import attr


@attr.s
class AccredToLoad(object):
    email = attr.ib(validator=attr.validators.instance_of(str), default='')
    unit = attr.ib(validator=attr.validators.instance_of(str), default='')
    right = attr.ib(validator=attr.validators.instance_of(str), default='WordPress Editor')
