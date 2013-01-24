from persistent.mapping import PersistentMapping


class VPTRoot(PersistentMapping):
    __parent__ = __name__ = None


def appmaker(zodb_root):
    if not 'vpt_root' in zodb_root:
        app_root = VPTRoot()
        zodb_root['app_root'] = app_root
        import transaction
        transaction.commit()
    return zodb_root['app_root']
