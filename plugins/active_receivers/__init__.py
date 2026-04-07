# -*- coding: utf-8 -*-
def classFactory(iface):
    from .active_receivers import ActiveReceivers
    return ActiveReceivers(iface)
