import sys
import traceback
import types
import argtest

class LoggerdebugSectionsTester:
  def test(self,value):
      if not value:
	  return (1,[])
      else:
	  return (1,value)

class Logger:
  debugLevel    = 1
  debugSections = []
  debugIndent   = '  '

  def __init__(self, argDB = None):
    self.setFromArgs(argDB)

  def setFromArgs(self, argDB):
    if not argDB: return
    argDB.setHelp('debugLevel', 'Integer 0 to 4')
    argDB.setTester('debugLevel',argtest.IntTester())
    self.debugLevel    = int(argDB['debugLevel'])
    argDB.setTester('debugSections',LoggerdebugSectionsTester())
    self.debugSections = argDB['debugSections']

  def debugListStr(self, list):
    if (self.debugLevel > 4) or (len(list) < 4):
      return str(list)
    else:
      return '['+str(list[0])+'-<'+str(len(list)-2)+'>-'+str(list[-1])+']'

  def debugPrint(self, msg, level = 1, section = None):
    indentLevel = len(traceback.extract_stack())-4
    if self.debugLevel >= level:
      if (not section) or (not self.debugSections) or (section in self.debugSections):
        for i in range(indentLevel):
          sys.stdout.write(self.debugIndent)
        print msg
