import babel
import bk
import BSTemplates.compileDefaults as compileDefaults
import fileset
import BSTemplates.sidlDefaults as sidlDefaults
import target
import transform

import os
import re

class Defaults:
  implRE = re.compile(r'^(.*)_Impl$')

  def __init__(self, project, sources = None, bootstrapPackages = []):
    self.project    = project
    self.sources    = sources
    self.usingSIDL  = sidlDefaults.UsingSIDL(project, self.getPackages(), bootstrapPackages = bootstrapPackages)
    self.compileExt = []
    # Add C for the IOR
    self.addLanguage('C')

  def getUsing(self, lang):
    return getattr(self, 'using'+lang.replace('+', 'x'))

  def addLanguage(self, lang):
    try:
      self.getUsing(lang.replace('+', 'x'))
    except AttributeError:
      lang = lang.replace('+', 'x')
      opt  = getattr(compileDefaults, 'Using'+lang)(self.usingSIDL)
      setattr(self, 'using'+lang, opt)
      self.compileExt.extend(opt.getCompileSuffixes())
    return

  def addClientLanguage(self, lang):
    self.usingSIDL.clientLanguages.append(lang)
    self.addLanguage(lang)

  def addServerLanguage(self, lang):
    self.usingSIDL.serverLanguages.append(lang)
    self.addLanguage(lang)

  def isImpl(self, source):
    if os.path.splitext(source)[1] == '.pyc':      return 0
    if self.implRE.match(os.path.dirname(source)): return 1
    return 0

  def isNewSidl(self, sources):
    if isinstance(sources, fileset.FileSet):
      if sources.tag == 'sidl' and len(sources) > 0:
        return 1
      else:
        return 0
    elif isinstance(sources, list):
      isNew = 0
      for source in sources:
        isNew = isNew or self.isNewSidl(source)
      return isNew
    else:
      raise RuntimeError('Invalid type for sources: '+type(sources))

  def getPackages(self):
    if self.sources:
      sources = self.sources
    else:
      sources = []
    return map(lambda file: os.path.splitext(os.path.split(file)[1])[0], sources)

  def getRepositoryTargets(self):
    action = babel.CompileSIDLRepository(compilerFlags = self.usingSIDL.getCompilerFlags())
    action.outputDir = self.usingSIDL.repositoryDir
    action.repositoryDirs.extend(self.usingSIDL.repositoryDirs)
    return [target.Target(None, [babel.TagAllSIDL(), action])]

  def getSIDLServerCompiler(self, lang, rootDir, generatedRoots):
    action = babel.CompileSIDLServer(fileset.ExtensionFileSet(generatedRoots, self.compileExt), compilerFlags = self.usingSIDL.getCompilerFlags())
    action.language  = lang
    action.outputDir = rootDir
    action.repositoryDirs.append(self.usingSIDL.repositoryDir)
    action.repositoryDirs.extend(self.usingSIDL.repositoryDirs)
    return action

  def getSIDLServerTargets(self):
    targets = []
    for lang in self.usingSIDL.serverLanguages:
      serverSourceRoots = fileset.FileSet(map(lambda package, lang=lang, self=self: self.usingSIDL.getServerRootDir(lang, package), self.getPackages()))
      for rootDir in serverSourceRoots:
        if not os.path.isdir(rootDir):
          os.makedirs(rootDir)

      genActions = [bk.TagBKOpen(roots = serverSourceRoots),
                    bk.BKOpen(),
                    # CompileSIDLServer() will add the package automatically to the output directory
                    self.getSIDLServerCompiler(lang, self.usingSIDL.getServerRootDir(lang), serverSourceRoots),
                    bk.TagBKClose(roots = serverSourceRoots),
                    transform.FileFilter(self.isImpl, tags = 'bkadd'),
                    bk.BKClose()]

      defActions = transform.Transform(fileset.ExtensionFileSet(serverSourceRoots, self.compileExt))

      targets.append(target.Target(None, [babel.TagSIDL(), target.If(self.isNewSidl, genActions, defActions)]))
    return targets

  def getSIDLClientCompiler(self, lang, rootDir):
    compiler           = babel.CompileSIDLClient(fileset.ExtensionFileSet(rootDir, self.compileExt), compilerFlags = self.usingSIDL.getCompilerFlags())
    compiler.language  = lang
    compiler.outputDir = rootDir
    compiler.repositoryDirs.append(self.usingSIDL.repositoryDir)
    compiler.repositoryDirs.extend(self.usingSIDL.repositoryDirs)
    return compiler

  def getSIDLClientTargets(self):
    targets = []
    for lang in self.usingSIDL.clientLanguages:
      targets.append(target.Target(None, [babel.TagAllSIDL(), self.getSIDLClientCompiler(lang, self.usingSIDL.getClientRootDir(lang))]))
    # Some clients have to be linked with the corresponding server (like the Bable bootstrap)
    for package in self.getPackages():
      for lang in self.usingSIDL.internalClientLanguages[package]:
        targets.append(target.Target(None, [babel.TagAllSIDL(), self.getSIDLClientCompiler(lang, self.usingSIDL.getServerRootDir(lang, package))]))
    return targets

  def getSIDLTarget(self):
    return target.Target(self.sources, [tuple(self.getRepositoryTargets()+self.getSIDLServerTargets()+self.getSIDLClientTargets()),
                                        transform.Update(),
                                        transform.SetFilter('old sidl')])
