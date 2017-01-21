
import workitem
import logging
_logger = logging.getLogger(__name__)


def create(cr, ident, wkf_id):
    (uid, res_type, res_id) = ident
    cr.execute('insert into wkf_instance (res_type,res_id,uid,wkf_id) values (%s,%s,%s,%s) RETURNING id',
               (res_type, res_id, uid, wkf_id))
    id_new = cr.fetchone()[0]
    cr.execute('select * from wkf_activity where flow_start=True and wkf_id=%s', (wkf_id,))
    res = cr.dictfetchall()
    _logger.debug('istance create: {}'.format(res))
    stack = []
    workitem.create(cr, res, id_new, ident, stack=stack)
    update(cr, id_new, ident)
    return id_new


def delete(cr, ident):
    (uid, res_type, res_id) = ident
    cr.execute('delete from wkf_instance where res_id=%s and res_type=%s', (res_id, res_type))


def validate(cr, inst_id, ident, signal, force_running=False):
    cr.execute("select * from wkf_workitem where inst_id=%s", (inst_id,))
    stack = []
    result = cr.dictfetchall()
    _logger.debug('istance validate: {}'.format(result))
    for witem in result:
        stack = []
        workitem.process(cr, witem, ident, signal, force_running, stack=stack)
        # An action is returned
    _update_end(cr, inst_id, ident)
    return stack and stack[0] or False


def update(cr, inst_id, ident):
    cr.execute("select * from wkf_workitem where inst_id=%s", (inst_id,))
    res = cr.dictfetchall()
    _logger.debug('istance update: {}'.format(res))
    for witem in res:
        stack = []
        workitem.process(cr, witem, ident, stack=stack)
    return _update_end(cr, inst_id, ident)


def _update_end(cr, inst_id, ident):
    cr.execute('select wkf_id from wkf_instance where id=%s', (inst_id,))
    wkf_id = cr.fetchone()[0]
    cr.execute(
        'select state,flow_stop from wkf_workitem w left join wkf_activity a on (a.id=w.act_id) where w.inst_id=%s',
        (inst_id,))
    ok = True
    for r in cr.fetchall():
        if (r[0] != 'complete') or not r[1]:
            ok = False
            break
    if ok:
        cr.execute('select distinct a.name from wkf_activity a left join wkf_workitem w on (a.id=w.act_id) where w.inst_id=%s', (inst_id,))
        act_names = cr.fetchall()
        cr.execute("update wkf_instance set state='complete' where id=%s", (inst_id,))
        cr.execute("update wkf_workitem set state='complete' where subflow_id=%s", (inst_id,))
        cr.execute("select i.id,w.osv,i.res_id from wkf_instance i left join wkf w on (i.wkf_id=w.id) where i.id IN (select inst_id from wkf_workitem where subflow_id=%s)", (inst_id,))
        for i in cr.fetchall():
            for act_name in act_names:
                validate(cr, i[0], (ident[0], i[1], i[2]), 'subflow.' + act_name[0])
    return ok