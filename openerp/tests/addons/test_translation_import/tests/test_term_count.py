import os
import unittest2

import openerp

UID = openerp.SUPERUSER_ID
DB = openerp.tools.config['db_name']

class TestTermCount(unittest2.TestCase):

    def setUp(self):
        self.cr = openerp.modules.registry.RegistryManager.get(DB).db.cursor()
        self.translation = openerp.modules.registry.RegistryManager.get(DB)['ir.translation']

    def tearDown(self):
        self.cr.rollback()
        self.cr.close()

    def test_count_term(self):
        "Just make sure we have as many entries as we wanted."
        ids = self.translation.search(self.cr, UID,
            [('src', '=', '1XBUO5PUYH2RYZSA1FTLRYS8SPCNU1UYXMEYMM25ASV7JC2KTJZQESZYRV9L8CGB')])
        self.assertEqual(len(ids), 2)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
