# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

import openerp.exceptions
import openerp.pooler as pooler
import openerp.tools as tools
from random import seed, sample
from string import ascii_letters, digits
import hashlib

# .apidoc title: Authentication helpers
magic_md5 = '$1$'


def gen_salt(length=8, symbols=ascii_letters + digits):
    seed()
    return ''.join(sample(symbols, length))


def encrypt_md5(raw_pw, salt, magic=magic_md5):
    raw_pw = raw_pw.encode('utf-8')
    salt = salt.encode('utf-8')
    hash = hashlib.md5()
    hash.update(raw_pw + magic + salt)
    st = hashlib.md5()
    st.update(raw_pw + salt + raw_pw)
    stretch = st.digest()

    for i in range(0, len(raw_pw)):
        hash.update(stretch[i % 16])

    i = len(raw_pw)

    while i:
        if i & 1:
            hash.update('\x00')
        else:
            hash.update(raw_pw[0])
        i >>= 1

    saltedmd5 = hash.digest()

    for i in range(1000):
        hash = hashlib.md5()

        if i & 1:
            hash.update(raw_pw)
        else:
            hash.update(saltedmd5)

        if i % 3:
            hash.update(salt)
        if i % 7:
            hash.update(raw_pw)
        if i & 1:
            hash.update(saltedmd5)
        else:
            hash.update(raw_pw)

        saltedmd5 = hash.digest()

    itoa64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

    rearranged = ''
    for a, b, c in ((0, 6, 12), (1, 7, 13), (2, 8, 14), (3, 9, 15), (4, 10, 5)):
        v = ord(saltedmd5[a]) << 16 | ord(saltedmd5[b]) << 8 | ord(saltedmd5[c])

        for i in range(4):
            rearranged += itoa64[v & 0x3f]
            v >>= 6

    v = ord(saltedmd5[11])

    for i in range(2):
        rearranged += itoa64[v & 0x3f]
        v >>= 6

    return magic + salt + '$' + rearranged


def login(db, login, password):
    pool = pooler.get_pool(db)
    user_obj = pool.get('res.users')
    return user_obj.login(db, login, password)


def check_super(passwd):
    stored_pw = tools.config['admin_passwd']
    # double password mode
    if stored_pw[0:len(magic_md5)] == magic_md5:
        salt = stored_pw[len(magic_md5):11]
        encrypted_pw = encrypt_md5(passwd, salt)
        if encrypted_pw == stored_pw:
            return True
        else:
            raise openerp.exceptions.AccessDenied()

    if passwd == stored_pw:
        return True
    else:
        raise openerp.exceptions.AccessDenied()


def check(db, uid, passwd):
    pool = pooler.get_pool(db)
    user_obj = pool.get('res.users')
    return user_obj.check(db, uid, passwd)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
