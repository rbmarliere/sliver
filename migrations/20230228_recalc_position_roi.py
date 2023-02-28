import core


for p in core.db.Position.select():
    print("Updating position %s" % p.id)
    if p.roi > 0:
        print("Old ROI: %s" % p.roi)
        p.roi = core.utils.get_roi(p.entry_cost, p.pnl)
        print("New ROI: %s" % p.roi)
        p.save()
