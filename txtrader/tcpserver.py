#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
  tcpserver.py
  ------------

  TxTrader TCP server module - Implement ASCII line oriented event interface.

  Copyright (c) 2015 Reliance Systems Inc. <mkrueger@rstms.net>
  Licensed under the MIT license.  See LICENSE for details.

"""

from version import __version__, __date__, __label__

import sys

from twisted.internet.protocol import Factory
from twisted.internet import reactor
from twisted.protocols import basic
from socket import gethostname

class tcpserver(basic.LineReceiver):
    def __init__(self):
        self.delimiter = '\n'
        self.commands = {
          'auth': self.cmd_auth,
          'help': self.cmd_help,
          'quit': self.cmd_disconnect,
          'exit': self.cmd_disconnect,
          'bye': self.cmd_disconnect,
          'status': self.cmd_status,
          'getbars': self.cmd_getbars,
          'marketorder': self.cmd_market_order,
          'stoporder': self.cmd_stop_order,
          'limitorder': self.cmd_limit_order,
          'stoplimitorder': self.cmd_stoplimit_order,
          'add': self.cmd_add,
          'del': self.cmd_del,
          'symbols': self.cmd_symbols,
          'positions': self.cmd_positions,
          'orders': self.cmd_orders,
          'executions': self.cmd_executions,
          'globalcancel': self.cmd_globalcancel,
          'cancel': self.cmd_cancel,
          'setaccount': self.cmd_setaccount,
          'accounts': self.cmd_accounts,
          'shutdown': self.cmd_shutdown,
        }
        self.authmap=set([])
    
    def lineReceived(self, line):
        line = line.strip()
        self.factory.output('user command: %s' % '%s xxxxxxxxxxx' % ' '.join(line.split()[:2]) if line.startswith('auth') else line)
        if line:
            cmd = line.split()[0]
            if cmd in self.commands.keys():
                if cmd=='auth' or self.check_authorized():
                    response=self.commands[cmd](line)
                    if response:
                        self.send(response)
            else:
                if self.check_authorized():
                    self.send('.what?')
        else:
          self.check_authorized()
          
    def send(self, msg):
        self.transport.write('%s\n' % msg)
          
    def cmd_auth(self, line):
        auth, username, password = line.split()[:3]
        if self.factory.validate(username, password):
            self.authmap.add(self.transport.getPeer())
            self.factory.api.open_client(self)
            return '.Authorized %s' % self.factory.api.channel
        else:
            self.check_authorized()
            
    def check_authorized(self):
        if not self.transport.getPeer() in self.authmap:
            self.transport.write('.Authorization required!\n')
            self.factory.api.close_client(self)
            self.transport.loseConnection() 
            return False
        return True
    
    def cmd_shutdown(self, line):
        self.factory.output('client at %s requested shutdown' % self.transport.getPeer())
        self.factory.api.close_client(self)
        reactor.callLater(1, reactor.stop)
          
    def cmd_help(self, line):
        self.transport.write('.commands: %s\n' % repr(self.commands.keys()))
        
    def cmd_disconnect(self, line):
        self.authmap.discard(self.transport.getPeer())
        self.transport.loseConnection()
      
    def cmd_status(self, line):
        self.transport.write('.status: %s\n' % self.factory.api.query_connection_status())

    def cmd_setaccount(self, line):
        setaccount, account = line.split()[:2]
        self.factory.api.set_account(account, self.transport.write)
        
    def cmd_accounts(self, line):
        self.transport.write('.accounts: %s\n' % self.factory.api.accounts)
    
    def cmd_getbars(self, line):
        bars, symbol, period, start_date, start_time, end_date, end_time =line.split()[:7]
        self.factory.api.query_bars(symbol, period, ' '.join((start_date, start_time)), ' '.join((end_date, end_time)), self.transport.write)
        []
    def cmd_add(self, line):
        add, symbol = line.split()[:2]
        self.factory.api.symbol_enable(symbol, self)
        self.transport.write('.symbol %s added\n' % symbol)
    
    def cmd_del(self, line):
        add, symbol = line.split()[:2]
        self.factory.api.symbol_disable(symbol, self)
        self.transport.write('.symbol %s deleted\n' % symbol)
    
    def cmd_market_order (self, line):
        order, symbol, qstr = line.split()[:3]
        self.factory.api.market_order(symbol, int(qstr), self.transport.write)
          
    def cmd_stop_order (self, line):
        order, symbol, price, qstr = line.split()[:4]
        self.factory.api.stop_order(symbol, float(price), int(qstr), self.transport.write)
          
    def cmd_limit_order (self, line):
        order, symbol, price, qstr = line.split()[:4]
        self.factory.api.limit_order(symbol, float(price), int(qstr), self.transport.write)
          
    def cmd_stoplimit_order (self, line):
        order, symbol, stop_price, limit_price, qstr = line.split()[:5]
        self.factory.api.stoplimit_order(symbol, float(stop_price), float(limit_price), int(qstr), self.transport.write)
          
    def cmd_cancel(self, line):
        cancel, id = line.split()[:2]
        self.factory.api.cancel_order(id, self.transport.write)
    
    def cmd_symbols(self, line):
        symbols = self.factory.api.symbols
        self.transport.write('.symbols: %s\n' % repr(symbols))
        
    def cmd_positions(self, line):
        self.factory.api.request_positions(self.transport.write)
    
    def cmd_orders(self, line):
        self.factory.api.request_orders(self.transport.write)
    
    def cmd_executions(self, line):
        self.factory.api.request_executions(self.transport.write)
    
    def cmd_globalcancel(self, line):
        self.factory.api.request_global_cancel()
        self.transport.write('.global order cancel requested\n')
    
    def connectionMade(self):
        self.factory.output('client connection from %s' % self.transport.getPeer())
        self.authmap.discard(self.transport.getPeer())
        self.transport.write('.connected: %s %s %s %s on %s\n' % (self.factory.api.label, __version__, __date__, __label__, gethostname()))
    
    def connectionLost(self, reason):
        self.factory.output('client connection from %s lost: %s' % (self.transport.getPeer(), repr(reason)))
        self.authmap.discard(self.transport.getPeer())
        self.factory.api.close_client(self)
    
class serverFactory(Factory):
    protocol = tcpserver
    def __init__(self, api):
        self.api= api
        self.output = api.output

    def validate(self, username, password):
        return username==self.api.username and password == self.api.password
    
