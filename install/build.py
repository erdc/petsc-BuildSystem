import install.retrieval
import install.urlMapping

import os
import sys

class Builder(install.urlMapping.UrlMapping):
  def __init__(self):
    install.urlMapping.UrlMapping.__init__(self)
    self.retriever = install.retrieval.Retriever()
    return

  def getMakeModule(self, root, name = 'make'):
    import imp

    (fp, pathname, description) = imp.find_module(name, [root])
    try:
      return imp.load_module(name, fp, pathname, description)
    finally:
      if fp: fp.close()

  def build(self, root, target = ['default'], setupTarget = None, ignoreDependencies = 0):
    self.debugPrint('Building '+str(target)+' in '+root, 1, 'install')
    try:
      maker = self.getMakeModule(root).PetscMake(sys.argv[1:], self.argDB)
    except ImportError:
      self.debugPrint('  No make module present in '+root, 2, 'install')
      return
    root = maker.getRoot()
    if not ignoreDependencies:
      for url in maker.executeTarget('getDependencies'):
        self.debugPrint('  Retrieving and activating dependency '+url, 2, 'install')
        self.build(self.retriever.retrieve(url), target = ['activate', 'configure'])
    # Load any existing local RDict
    dictFilename = os.path.join(root, 'RDict.db')
    loadedRDict  = 0
    if os.path.exists(dictFilename):
      try:
        import cPickle
        dbFile = file(dictFilename)
        data   = cPickle.load(dbFile)
        self.debugPrint('Loaded argument database from '+dictFilename, 2, 'install')
        keys   = self.argDB.keys()
        for k in filter(lambda k: not k in keys, data.keys()):
          if data[k].isValueSet():
            self.argDB.setType(k, data[k])
          self.debugPrint('Set key "'+str(k)+'" in argument database', 4, 'install')
        dbFile.close()
        loadedRDict = 1
      except Exception, e:
        self.debugPrint('Problem loading dictionary from '+dictFilename+'\n--> '+str(e), 2, 'install')
        raise e
    self.debugPrint('Compiling in '+root, 2, 'install')
    if setupTarget is None:                 setupTarget = []
    elif not isinstance(setupTarget, list): setupTarget = [setupTarget]
    for t in setupTarget:
      maker.executeTarget(t)
    ret = maker.main(target)
    if loadedRDict:
      for k in filter(lambda k: not k in keys, data.keys()):
        if data[k].isValueSet():
          del self.argDB[k]
    if not ignoreDependencies:
      for url in maker.executeTarget('getDependencies'):
        self.debugPrint('  Installing dependency '+url, 2, 'install')
        self.build(self.getInstallRoot(url), target = ['install'])
      maker.executeTarget('install')
    # Save source database (since atexit() functions might not be called before another build)
    maker.sourceDB.save()
    return ret
