from modules.Packages import Package
from modules.Packages import loadPackages, savePackageInfo, LocalDB
import optparse
from modules.ImportPathDB import ImportPathDB
from modules.Utils import FormatedPrint
from modules.ImportPathDB import ImportPathDBCache
from modules.Config import Config

from time import time, strftime, gmtime
import sys
import os

def createDB(full=False, verbose=False):
	scan_time_start = time()
	packages = []
	outdated = {}
	valid = {}

	if full:
		packages = loadPackages()
	else:
		print "Creating list of updated builds..."
		err, outdated  = LocalDB().getOutdatedBuilds()
		if err != []:
			print "Warning: " + "\nWarning: ".join(err)

		packages = outdated.keys()

	if verbose:
		print "Packages to be scanned:"
		for pkg in packages:
			print "\t%s" % pkg
		print ""

	pkg_cnt = len(packages)
	pkg_idx = 1

	pkg_name_len = 0
	for package in packages:
		l = len(package)
		if l > pkg_name_len:
			pkg_name_len = l

	pkg_cnt_len = len("%s" % pkg_cnt)

	print "Updating spec file provides..."
	err, ret = LocalDB().updatePackages(packages)
	if not ret:
		print "Error:\n" + "\n".join(err)
		return False	

	ipdb_cache = ImportPathDBCache()
	if not ipdb_cache.load():
		print "Error: %s" % ipdb_cache.getError()
		return False

	golang_pkg = Config().getGolangPkgdb()

	for package in packages:
		starttime = time()
		# len of pkg_idx
		pkg_idx_len = len("%s" % pkg_idx)
		sys.stdout.write("Scanning %s %s %s%s/%s " % (package, (pkg_name_len - len(package) + 3) * ".", (pkg_cnt_len - pkg_idx_len) * " " , pkg_idx, pkg_cnt))
		sys.stdout.flush()
		pkg = Package(package)
		info = pkg.getInfo()
		# save xml into file
		errs = savePackageInfo(info)
		if errs != []:
			print ""
			print "\n".join(errs)
		else:
			if not full:
				valid[package] = outdated[package]

		pkg_idx += 1
		endtime = time()
		elapsedtime = endtime - starttime
		print strftime("[%Hh %Mm %Ss]", gmtime(elapsedtime))

		# update cache of imported and provided packages
		for item in info:
			devel_name = item

			# This is hacky and depends on info data type represenation
			pkg2xml_obj = info[item]['xmlobj']
			if pkg2xml_obj.getError() != "":
				continue
			imports = pkg2xml_obj.getImportedPackages()
			provides = pkg2xml_obj.getProvidedPackages()

			ipdb_cache.updateBuild(devel_name, provides, imports, package)


	if not ipdb_cache.flush():
		print ipdb_cache.getError()

	scan_time_end = time()
	print strftime("Elapsed time %Hh %Mm %Ss", gmtime(scan_time_end - scan_time_start))

	if not full:
		LocalDB().updateBuildsInCache(valid)

	return True

def displayPaths(paths, prefix = '', minimal = False):
	for pkg in paths:
		found = False
		ips = []
		for path in paths[pkg]:
			if path.startswith(prefix):
				found = True
				ips.append(path)

		if found:
			print pkg
			if not minimal:
				for ip in ips:
					print "\t%s" % ip

if __name__ == "__main__":

	parser = optparse.OptionParser("%prog [-c [-f]] [-i|-p [-s [-m]]]")

	#parser.add_option_group( optparse.OptionGroup(parser, "directory", "Directory to inspect. If empty, current directory is used.") )

	parser.add_option(
	    "", "-c", "--create", dest="create", action = "store_true", default = False,
	    help = "Create database of import and imported paths for all available builds of golang devel source packages"
	)

	parser.add_option(
	    "", "-f", "--full", dest="full", action = "store_true", default = False,
	    help = "Regenerate the entire database. Default is to regenerate only updated builds."
	)

	parser.add_option(
	    "", "-i", "--imported", dest="imports", action = "store_true", default = False,
	    help = "List all import paths devel packages need"
	)

	parser.add_option(
	    "", "-p", "--provided", dest="provides", action = "store_true", default = False,
	    help = "List all import paths devel packages provide"
	)

	parser.add_option(
	    "", "-s", "--prefix", dest="prefix", default = "",
	    help = "Prefix of import paths to display. Used with -i and -p options."
	)

	parser.add_option(
	    "", "-m", "--minimal", dest="minimal", action = "store_true",  default = False,
	    help = "List only packages. Used with -s option."
	)

	parser.add_option(
	    "", "-v", "--verbose", dest="verbose", action = "store_true",  default = False,
	    help = "Verbose mode."
	)

	options, args = parser.parse_args()

	fmt_obj = FormatedPrint(formated=False)

	if options.imports and options.provides:
		print "You can not set both -i and -o options at the same time"
		exit(1)

	if options.create:
		if createDB(full=options.full, verbose=options.verbose):
			print "DB updated"
		else:
			print "DB not updated"

	elif options.imports:
		ipdb_obj = ImportPathDB()
		if not ipdb_obj.load():
			fmt_obj.printError(ipdb_obj.getError())
			exit(1)

		paths = ipdb_obj.getImportedPaths()
		displayPaths(paths, options.prefix, options.minimal)
	elif options.provides:
		ipdb_obj = ImportPathDB()
		if not ipdb_obj.load():
			fmt_obj.printError(ipdb_obj.getError())
			exit(1)

		paths = ipdb_obj.getProvidedPaths()
		displayPaths(paths, options.prefix, options.minimal)
	else:
		print "Synopsis: prog [-c [-f]] [-i|-p [-s [-m]]]"
		exit(1)

	exit(0)
