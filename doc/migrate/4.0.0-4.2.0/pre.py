# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

__author__ = 'Cédric Krier, <ced@tinyerp.com>'
__version__ = '0.1.0'

import psycopg
import optparse
import ConfigParser

# -----

parser = optparse.OptionParser(version="Tiny ERP server migration script " + __version__)

parser.add_option("-c", "--config", dest="config", help="specify path to Tiny ERP config file")

group = optparse.OptionGroup(parser, "Database related options")
group.add_option("--db_host", dest="db_host", help="specify the database host") 
group.add_option("--db_port", dest="db_port", help="specify the database port") 
group.add_option("-d", "--database", dest="db_name", help="specify the database name")
group.add_option("-r", "--db_user", dest="db_user", help="specify the database user name")
group.add_option("-w", "--db_password", dest="db_password", help="specify the database password") 
parser.add_option_group(group)

options = optparse.Values()
options.db_name = 'terp' # default value
parser.parse_args(values=options)

if hasattr(options, 'config'):
	configparser = ConfigParser.ConfigParser()
	configparser.read([options.config])
	for name, value in configparser.items('options'):
		if not (hasattr(options, name) and getattr(options, name)):
			if value in ('true', 'True'):
				value = True
			if value in ('false', 'False'):
				value = False
			setattr(options, name, value)

# -----

host = hasattr(options, 'db_host') and "host=%s" % options.db_host or ''
port = hasattr(options, 'db_port') and "port=%s" % options.db_port or ''
name = "dbname=%s" % options.db_name
user = hasattr(options, 'db_user') and "user=%s" % options.db_user or ''
password = hasattr(options, 'db_password') and "password=%s" % options.db_password or ''

db = psycopg.connect('%s %s %s %s %s' % (host, port, name, user, password), serialize=0)
cr = db.cursor()

# ----------------------------- #
# drop constraint on ir_ui_view #
# ----------------------------- #

cr.execute('SELECT conname FROM pg_constraint where conname = \'ir_ui_view_type\'')
if cr.fetchall():
	cr.execute('ALTER TABLE ir_ui_view DROP CONSTRAINT ir_ui_view_type')
cr.commit()

# ------------------------ #
# update res.partner.bank  #
# ------------------------ #

cr.execute('SELECT a.attname FROM pg_class c, pg_attribute a WHERE c.relname = \'res_partner_bank\' AND a.attname = \'iban\' AND c.oid = a.attrelid')
if cr.fetchall():
	cr.execute('ALTER TABLE res_partner_bank RENAME iban TO acc_number')
cr.commit()

# ------------------------------------------- #
# Add perm_id to ir_model and ir_model_fields #
# ------------------------------------------- #

cr.execute('SELECT a.attname FROM pg_class c, pg_attribute a WHERE c.relname = \'ir_model\' AND a.attname = \'perm_id\' AND c.oid = a.attrelid')
if not cr.fetchall():
	cr.execute("ALTER TABLE ir_model ADD perm_id int references perm on delete set null")
cr.commit()

cr.execute('SELECT a.attname FROM pg_class c, pg_attribute a WHERE c.relname = \'ir_model_fields\' AND a.attname = \'perm_id\' AND c.oid = a.attrelid')
if not cr.fetchall():
	cr.execute("ALTER TABLE ir_model_fields ADD perm_id int references perm on delete set null")
cr.commit()


# --------------------------------- #
# remove name for all ir_act_window #
# --------------------------------- #

cr.execute("UPDATE ir_act_window SET name = ''")
cr.commit()

# ------------------------------------------------------------------------ #
# Create a "allow none" default access to keep the behaviour of the system #
# ------------------------------------------------------------------------ #

cr.execute('SELECT model_id FROM ir_model_access')
res= cr.fetchall()
for r in res:
	cr.execute('SELECT id FROM ir_model_access WHERE model_id = %d AND groupd_id IS NULL', (r[0],))
	if not cr.fetchall():
		cr.execute("INSERT into ir_model_access (name,model_id,group_id) VALUES ('Auto-generated access by migration',%d,NULL)",(r[0],))
cr.commit()

# ------------------------------------------------- #
# Drop view report_account_analytic_line_to_invoice #
# ------------------------------------------------- #

cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_account_analytic_line_to_invoice\'')
if cr.fetchall():
	cr.execute('DROP VIEW report_account_analytic_line_to_invoice')
cr.commit()

# --------------------------- #
# Drop state from hr_employee #
# --------------------------- #

cr.execute('SELECT * FROM pg_class c, pg_attribute a WHERE c.relname=\'hr_employee\' AND a.attname=\'state\' AND c.oid=a.attrelid')
if cr.fetchall():
	cr.execute('ALTER TABLE hr_employee DROP state')
cr.commit()

# ------------ #
# Add timezone #
# ------------ #

cr.execute('SELECT id FROM ir_values where model=\'res.users\' AND key=\'meta\' AND name=\'tz\'')
if not cr.fetchall():
	import pytz, pickle
	meta = pickle.dumps({'type':'selection', 'string':'Timezone', 'selection': [(x, x) for x in pytz.all_timezones]})
	value = pickle.dumps(False)
	cr.execute('INSERT INTO ir_values (name, key, model, meta, key2, object, value) VALUES (\'tz\', \'meta\', \'res.users\', %s, \'tz\', %s, %s)', (meta,False, value))
cr.commit()

# -------------------- #
# Change currency rate #
# -------------------- #

cr.execute('SELECT a.attname FROM pg_class c, pg_attribute a WHERE c.relname = \'res_currency_rate\' AND a.attname = \'rate_old\' AND c.oid = a.attrelid')
if not cr.fetchall():
	cr.execute('ALTER TABLE res_currency_rate ADD rate_old NUMERIC(12,6)')
	cr.execute('UPDATE res_currency_rate SET rate_old = rate')
	cr.execute('UPDATE res_currency_rate SET rate = (1 / rate_old)')
cr.commit()

cr.close
