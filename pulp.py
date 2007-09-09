# PuLP : Python LP Modeler
# @(#) $Jeannot: pulp.py,v 1.84 2005/05/05 09:23:51 js Exp $

# Copyright (c) 2002-2005, Jean-Sebastien Roy (js@jeannot.org)

# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
PuLP: An LP modeler in Python

PuLP is an LP modeler written in python. PuLP can generate MPS or LP files
and call GLPK, COIN CLP/CBC, CPLEX and XPRESS to solve linear problems.

Use LpVariable() to create new variables. ex:
x = LpVariable("x", 0, 3)
to create a variable 0 <= x <= 3

Use LpProblem() to create new problems. ex:
prob = LpProblem("myProblem", LpMinimize)

Combine variables to create expressions and constraints and add them to the
problem. ex:
prob += x + y <= 2
If you add an expression (not a constraint, f.e. prob += 4*z + w), it will
become the objective.

Choose a solver and solve the problem. ex:
prob.solve(GLPK())

You can get the value of the variables using value(). ex:
value(x)
"""
import os

# variable categories
LpContinuous = 0
LpInteger = 1
LpCategories = {LpContinuous: "Continuous", LpInteger: "Integer"}

# objective sense
LpMinimize = 1
LpMaximize = -1
LpSenses = {LpMaximize:"Maximize", LpMinimize:"Minimize"}

# problem status
LpStatusNotSolved = 0
LpStatusOptimal = 1
LpStatusFeasible = 2
LpStatusInfeasible = -1
LpStatusUnbounded = -2
LpStatusUndefined = -3
LpStatus = { LpStatusNotSolved:"Not Solved",
	LpStatusOptimal:"Optimal",
	LpStatusFeasible:"Feasible",
	LpStatusInfeasible:"Infeasible",
	LpStatusUnbounded:"Unbounded",
	LpStatusUndefined:"Undefined",
	}

# constraint sense
LpConstraintLE = -1
LpConstraintEQ = 0
LpConstraintGE = 1
LpConstraintSenses = {LpConstraintEQ:"=", LpConstraintLE:"<=", LpConstraintGE:">="}

# LP line size
LpCplexLPLineSize = 78

# See later for LpSolverDefault definition

class LpSolver:
	"""A generic LP Solver"""

	def __init__(self, mip = 1, msg = 1, options = []):
		self.mip = mip
		self.msg = msg
		self.options = options

	def available(self):
		"""True if the solver is available"""
		raise NotImplementedError

	def actualSolve(self, lp):
		"""Solve a well formulated lp problem"""
		raise NotImplementedError

	def copy(self):
		"""Make a copy of self"""
		
		aCopy = self.__class__()
		aCopy.mip = self.mip
		aCopy.msg = self.msg
		aCopy.options = self.options
		return aCopy

	def solve(self, lp):
		"""Solve the problem lp"""
		# Always go through the solve method of LpProblem
		return lp.solve(self)

class LpSolver_CMD(LpSolver):
	"""A generic command line LP Solver"""
	def __init__(self, path = None, keepFiles = 0, mip = 1, msg = 1, options = []):
		LpSolver.__init__(self, mip, msg, options)
		if path is None:
			self.path = self.defaultPath()
		else:
			self.path = path
		self.keepFiles = keepFiles
		self.setTmpDir()

	def copy(self):
		"""Make a copy of self"""
		
		aCopy = LpSolver.copy(self)
		aCopy.path = self.path
		aCopy.keepFiles = self.keepFiles
		aCopy.tmpDir = self.tmpDir
		return aCopy

	def setTmpDir(self):
		"""Set the tmpDir attribute to a reasonnable location for a temporary
		directory"""
		if os.name != 'nt':
			# On unix use /tmp by default
			self.tmpDir = os.environ.get("TMPDIR", "/tmp")
			self.tmpDir = os.environ.get("TMP", self.tmpDir)
		else:
			# On Windows use the current directory
			self.tmpDir = os.environ.get("TMPDIR", "")
			self.tmpDir = os.environ.get("TMP", self.tmpDir)
			self.tmpDir = os.environ.get("TEMP", self.tmpDir)
		if not os.path.isdir(self.tmpDir):
			self.tmpDir = ""
		elif not os.access(self.tmpDir, os.F_OK + os.W_OK):
			self.tmpDir = ""

	def defaultPath(self):
		raise NotImplementedError

	def executableExtension(name):
		if os.name != 'nt':
			return name
		else:
			return name+".exe"
	executableExtension = staticmethod(executableExtension)

	def executable(command):
		"""Checks that the solver command is executable,
		And returns the actual path to it."""

		if os.path.isabs(command):
			if os.access(command, os.X_OK):
				return command
		for path in os.environ.get("PATH", []).split(os.pathsep):
			if os.access(os.path.join(path, command), os.X_OK):
				return os.path.join(path, command)
		return False
	executable = staticmethod(executable)

class GLPK_CMD(LpSolver_CMD):
	"""The GLPK LP solver"""
	def defaultPath(self):
		return self.executableExtension("glpsol")

	def available(self):
		"""True if the solver is available"""
		return self.executable(self.path)

	def actualSolve(self, lp):
		"""Solve a well formulated lp problem"""
		if not self.executable(self.path):
			raise "PuLP: cannot execute "+self.path
		if not self.keepFiles:
			pid = os.getpid()
			tmpLp = os.path.join(self.tmpDir, "%d-pulp.lp" % pid)
			tmpSol = os.path.join(self.tmpDir, "%d-pulp.sol" % pid)
		else:
			tmpLp = lp.name+"-pulp.lp"
			tmpSol = lp.name+"-pulp.sol"
		lp.writeLP(tmpLp, writeSOS = 0)
		proc = ["glpsol", "--lpt", tmpLp, "-o", tmpSol]
		if not self.mip: proc.append('--nomip')
		proc.extend(self.options)
		if not self.msg:
			proc[0] = self.path
			f = os.popen(" ".join(proc))
			f.read()
			rc = f.close()
			if rc != None:
				raise "PuLP: Error while trying to execute "+self.path
		else:
			if os.name != 'nt':
				rc = os.spawnvp(os.P_WAIT, self.path, proc)
			else:
				rc = os.spawnv(os.P_WAIT, self.executable(self.path), proc)
			if rc == 127:
				raise "PuLP: Error while trying to execute "+self.path
		if not os.path.exists(tmpSol):
			raise "PuLP: Error while executing "+self.path
		lp.status, values = self.readsol(tmpSol)
		lp.assign(values)
		if not self.keepFiles:
			try: os.remove(tmpLp)
			except: pass
			try: os.remove(tmpSol)
			except: pass
		return lp.status

	def readsol(self,filename):
		"""Read a GLPK solution file"""
		f = file(filename)
		f.readline()
		rows = int(f.readline().split()[1])
		cols = int(f.readline().split()[1])
		f.readline()
		statusString = f.readline()[12:-1]
		glpkStatus = {
			"INTEGER OPTIMAL":LpStatusOptimal,
			"INTEGER NON-OPTIMAL":LpStatusFeasible,
			"OPTIMAL":LpStatusOptimal,
			"INFEASIBLE (FINAL)":LpStatusInfeasible,
			"INTEGER EMPTY":LpStatusInfeasible,
			"INTEGER UNDEFINED":LpStatusUndefined,
			"UNBOUNDED":LpStatusUnbounded,
			"UNDEFINED":LpStatusUndefined
			}
		if statusString not in glpkStatus:
			raise ValueError, "Unknow status returned by GLPK: "+statusString
		status = glpkStatus[statusString]
		isInteger = statusString in ["INTEGER OPTIMAL","INTEGER UNDEFINED"]
		values = {}
		for i in range(4): f.readline()
		for i in range(rows):
			line = f.readline().split()
			if len(line) ==2: f.readline()
		for i in range(3):
			f.readline()
		for i in range(cols):
			line = f.readline().split()
			name = line[1]
			if len(line) ==2: line = [0,0]+f.readline().split()
			if isInteger:
				if line[2] == "*": value = int(line[3])
				else: value = float(line[2])
			else:
				value = float(line[3])
			values[name] = value
		return status, values

try:
	import pulpGLPK
	
	class GLPK_MEM(LpSolver):
		"""The GLPK LP solver (via a module)"""
		def __init__(self, mip = 1, msg = 1, presolve = 1):
			LpSolver.__init__(self, mip, msg)
			self.presolve = presolve

		def copy(self):
			"""Make a copy of self"""
		
			aCopy = LpSolver.copy()
			aCopy.presolve = self.presolve
			return aCopy

		def available(self):
			"""True if the solver is available"""
			return True

		def actualSolve(self, lp):
			"""Solve a well formulated lp problem"""
			lp.status = pulpGLPK.solve(lp.objective, lp.constraints, lp.sense, self.msg,
				self.mip, self.presolve)
			return lp.status
	
	GLPK = GLPK_MEM
except:
	class GLPK_MEM(LpSolver):
		"""The GLPK LP solver (via a module)"""
		def available(self):
			"""True if the solver is available"""
			return False

		def actualSolve(self, lp):
			"""Solve a well formulated lp problem"""
			raise RuntimeError, "GLPK_MEM: Not Available"

	GLPK = GLPK_CMD

class CPLEX_CMD(LpSolver_CMD):
	"""The CPLEX LP solver"""
	def defaultPath(self):
		return self.executableExtension("cplex")

	def available(self):
		"""True if the solver is available"""
		return self.executable(self.path)

	def actualSolve(self, lp):
		"""Solve a well formulated lp problem"""
		if not self.executable(self.path):
			raise "PuLP: cannot execute "+self.path
		if not self.keepFiles:
			pid = os.getpid()
			tmpLp = os.path.join(self.tmpDir, "%d-pulp.lp" % pid)
			# Should probably use another CPLEX solution format
			tmpSol = os.path.join(self.tmpDir, "%d-pulp.txt" % pid)
		else:
			tmpLp = lp.name+"-pulp.lp"
			# Should probably use another CPLEX solution format
			tmpSol = lp.name+"-pulp.txt"
		lp.writeLP(tmpLp, writeSOS = 1)
		try: os.remove(tmpSol)
		except: pass
		if not self.msg:
			cplex = os.popen(self.path+" > /dev/null 2> /dev/null", "w")
		else:
			cplex = os.popen(self.path, "w")
		cplex.write("read "+tmpLp+"\n")
		for option in self.options:
			cplex.write(option+"\n")
		if lp.isMIP():
			if self.mip:
				cplex.write("mipopt\n")
				cplex.write("change problem fixed\n")
			else:
				cplex.write("change problem relaxed_milp\n")
				
		cplex.write("optimize\n")
		cplex.write("write "+tmpSol+"\n")
		cplex.write("quit\n")
		if cplex.close() != None:
			raise "PuLP: Error while trying to execute "+self.path
		if not self.keepFiles:
			try: os.remove(tmpLp)
			except: pass
		if not os.path.exists(tmpSol):
			status = LpStatusInfeasible
		else:
			status, values = self.readsol(tmpSol)
		if not self.keepFiles:
			try: os.remove(tmpSol)
			except: pass
			try: os.remove("cplex.log")
			except: pass
		if status != LpStatusInfeasible:
			lp.assign(values)
		lp.status = status
		return status

	def readsol(self,filename):
		"""Read a CPLEX solution file"""
		f = file(filename)
		for i in range(3): f.readline()
		statusString = f.readline()[18:30]
		cplexStatus = {
			"OPTIMAL SOLN":LpStatusOptimal,
			}
		if statusString not in cplexStatus:
			raise ValueError, "Unknow status returned by CPLEX: "+statusString
		status = cplexStatus[statusString]

		while 1:
			l = f.readline()
			if l[:10] == " SECTION 2": break
		
		for i in  range(3): f.readline()
		values = {}
		while 1:
			l = f.readline()
			if l == "": break
			line = l[3:].split()
			if len(line):
				name = line[1]
				value = float(line[3])
				values[name] = value

		return status, values

try:
	import pulpCPLEX
	
	class CPLEX_MEM(LpSolver):
		"""The CPLEX LP solver (via a module)"""
		def __init__(self, mip = 1, msg = 1, timeLimit = -1):
			LpSolver.__init__(self, mip, msg)
			self.timeLimit = timeLimit

		def available(self):
			"""True if the solver is available"""
			return True

		def grabLicence(self):
			"""Returns True if a CPLEX licence can be obtained.
			The licence is kept until releaseLicence() is called."""
			return pulpCPLEX.grabLicence()

		def releaseLicence(self):
			"""Release a previously obtained CPLEX licence"""
			pulpCPLEX.releaseLicence()

		def actualSolve(self, lp):
			"""Solve a well formulated lp problem"""
			lp.status = pulpCPLEX.solve(lp.objective, lp.constraints, lp.sense, self.msg,
				self.mip, self.timeLimit)
			return lp.status
	
	CPLEX = CPLEX_MEM
except:
	class CPLEX_MEM(LpSolver):
		"""The CPLEX LP solver (via a module)"""
		def available(self):
			"""True if the solver is available"""
			return False
		def actualSolve(self, lp):
			"""Solve a well formulated lp problem"""
			raise RuntimeError, "CPLEX_MEM: Not Available"

	CPLEX = CPLEX_CMD

class XPRESS(LpSolver_CMD):
	"""The XPRESS LP solver"""
	def defaultPath(self):
		return self.executableExtension("optimizer")

	def available(self):
		"""True if the solver is available"""
		return self.executable(self.path)

	def actualSolve(self, lp):
		"""Solve a well formulated lp problem"""
		if not self.executable(self.path):
			raise "PuLP: cannot execute "+self.path
		if not self.keepFiles:
			pid = os.getpid()
			tmpLp = os.path.join(self.tmpDir, "%d-pulp.lp" % pid)
			tmpSol = os.path.join(self.tmpDir, "%d-pulp.prt" % pid)
		else:
			tmpLp = lp.name+"-pulp.lp"
			tmpSol = lp.name+"-pulp.prt"
		lp.writeLP(tmpLp, writeSOS = 1, mip = self.mip)
		if not self.msg:
			xpress = os.popen(self.path+" "+lp.name+" > /dev/null 2> /dev/null", "w")
		else:
			xpress = os.popen(self.path+" "+lp.name, "w")
		xpress.write("READPROB "+tmpLp+"\n")
		if lp.sense == LpMaximize:
			xpress.write("MAXIM\n")
		else:
			xpress.write("MINIM\n")
		if lp.isMIP() and self.mip:
			xpress.write("GLOBAL\n")
		xpress.write("WRITEPRTSOL "+tmpSol+"\n")
		xpress.write("QUIT\n")
		if xpress.close() != None:
			raise "PuLP: Error while executing "+self.path
		status, values = self.readsol(tmpSol)
		if not self.keepFiles:
			try: os.remove(tmpLp)
			except: pass
			try: os.remove(tmpSol)
			except: pass
		lp.status = status
		lp.assign(values)
		if abs(lp.infeasibilityGap(self.mip)) > 1e-5: # Arbitrary
			lp.status = LpStatusInfeasible
		return lp.status

	def readsol(self,filename):
		"""Read an XPRESS solution file"""
		f = file(filename)
		for i in range(6): f.readline()
		l = f.readline().split()

		rows = int(l[2])
		cols = int(l[5])
		for i in range(3): f.readline()
		statusString = f.readline().split()[0]
		xpressStatus = {
			"Optimal":LpStatusOptimal,
			}
		if statusString not in xpressStatus:
			raise ValueError, "Unknow status returned by XPRESS: "+statusString
		status = xpressStatus[statusString]
		values = {}
		while 1:
			l = f.readline()
			if l == "": break
			line = l.split()
			if len(line) and line[0] == 'C':
				name = line[2]
				value = float(line[4])
				values[name] = value
		return status, values

class COIN_CMD(LpSolver_CMD):
	"""The COIN CLP/CBC LP solver"""
	def defaultPath(self):
		return (self.executableExtension("clp"), self.executableExtension("cbc"))

	def __init__(self, path = None, keepFiles = 0, mip = 1,
			msg = 1, cuts = 1, presolve = 1, dual = 1, strong = 5, options = []):
		"""Here, path is a tuple containing the path to clp and cbc"""
		LpSolver_CMD.__init__(self, path, keepFiles, mip, msg, options)
		self.cuts = cuts
		self.presolve = presolve
		self.dual = dual
		self.strong = strong

	def copy(self):
		"""Make a copy of self"""
		
		aCopy = LpSolver_CMD.copy(self)
		aCopy.cuts = self.cuts
		aCopy.presolve = self.presolve
		aCopy.dual = self.dual
		aCopy.strong = self.strong
		return aCopy

	def actualSolve(self, lp):
		"""Solve a well formulated lp problem"""
		if lp.isMIP() and self.mip: return self.solve_CBC(lp)
		else: return self.solve_CLP(lp)

	def available(self):
		"""True if the solver is available"""
		return self.executable(self.path[0]) and \
			self.executable(self.path[1])

	def solve_CBC(self, lp):
		"""Solve a MIP problem using CBC"""
		if not self.executable(self.path[1]):
			raise "PuLP: cannot execute "+self.path[1]
		if not self.keepFiles:
			pid = os.getpid()
			tmpLp = os.path.join(self.tmpDir, "%d-pulp.mps" % pid)
			tmpSol = os.path.join(self.tmpDir, "%d-pulp.sol" % pid)
		else:
			tmpLp = lp.name+"-pulp.mps"
			tmpSol = lp.name+"-pulp.sol"
##		vs, variablesNames, constraintsNames, objectiveName = lp.writeMPS(tmpLp, rename = 1)
		vs = lp.writeMPS(tmpLp, rename = 0)
		if not self.msg:
			cbc = os.popen(self.path[1]+" - > /dev/null 2> /dev/null","w")
		else:
			cbc = os.popen(self.path[1]+" -","w")
		cbc.write("import "+tmpLp+"\n")
		if self.presolve:
			cbc.write("presolve on\n")
		cbc.write("strong %d\n" % self.strong)
		if self.cuts:
			cbc.write("gomory on\n")
			cbc.write("oddhole on\n")
			cbc.write("knapsack on\n")
			cbc.write("probing on\n")
		for option in self.options:
			cbc.write(option+"\n")
		if lp.sense == LpMinimize:
			cbc.write("min\n")
		else:
			cbc.write("max\n")
		if self.mip:
			cbc.write("branch\n")
		else:
			cbc.write("initialSolve\n")
		cbc.write("solution "+tmpSol+"\n")
		cbc.write("quit\n")
		if cbc.close() != None:
			raise "PuLP: Error while trying to execute "+self.path[1]
		if not os.path.exists(tmpSol):
			raise "PuLP: Error while executing "+self.path[1]
		lp.status, values = self.readsol_CBC(tmpSol, lp, vs)
		lp.assign(values)
		if not self.keepFiles:
			try: os.remove(tmpLp)
			except: pass
			try: os.remove(tmpSol)
			except: pass
		return lp.status

	def solve_CLP(self, lp):
		"""Solve a problem using CLP"""
		if not self.executable(self.path[0]):
			raise "PuLP: cannot execute "+self.path[0]
		if not self.keepFiles:
			pid = os.getpid()
			tmpLp = os.path.join(self.tmpDir, "%d-pulp.mps" % pid)
			tmpSol = os.path.join(self.tmpDir, "%d-pulp.sol" % pid)
		else:
			tmpLp = lp.name+"-pulp.mps"
			tmpSol = lp.name+"-pulp.sol"
		vs, variablesNames, constraintsNames, objectiveName = lp.writeMPS(tmpLp, rename = 1)
		if not self.msg:
			clp = os.popen(self.path[0]+" - > /dev/null 2> /dev/null","w")
		else:
			clp = os.popen(self.path[0]+" -","w")
		clp.write("import "+tmpLp+"\n")
		if self.presolve:
			clp.write("presolve on\n")
		for option in self.options:
			clp.write(option+"\n")
		if lp.sense == LpMinimize:
			clp.write("min\n")
		else:
			clp.write("max\n")
		if self.dual:
			clp.write("dualS\n")
		else:
			clp.write("primalS\n")
		clp.write("solution "+tmpSol+"\n")
		clp.write("quit\n")
		if clp.close() != None:
			raise "PuLP: Error while trying to execute "+self.path[0]
		if not os.path.exists(tmpSol):
			raise "PuLP: Error while executing "+self.path[0]
		lp.status, values = self.readsol_CLP(tmpSol, lp, vs, variablesNames, constraintsNames, objectiveName)
		lp.assign(values)
		if not self.keepFiles:
			try: os.remove(tmpLp)
			except: pass
			try: os.remove(tmpSol)
			except: pass
		return lp.status

	def readsol_CLP(self,filename, lp, vs, variablesNames, constraintsNames, objectiveName):
		"""Read a CLP solution file"""
		values = {}

		reverseVn = {}
		for k,n in variablesNames.iteritems():
			reverseVn[n] = k

		for v in vs:
			values[v.name] = 0.0

		status = LpStatusOptimal # status is very approximate
		f = file(filename)
		for l in f:
			if len(l)<=2: break
			if l[:2] == "**":
				status = LpStatusInfeasible
				l = l[2:]
			l = l.split()
			vn = l[1]
			if vn in reverseVn:
				values[reverseVn[vn]] = float(l[2])
		return status, values

	def readsol_CBC(self,filename, lp, vs):
		"""Read a CBC solution file"""
		f = file(filename)
##		for i in range(len(lp.constraints)): f.readline()
		values = {}
		for v in vs:
			values[v.name] = 0.0
			pass
		for line in f:
			l = line.split()
			values[l[1]] = float(l[2])
			pass
##		for v in vs:
##			l = f.readline().split()
##			values[v.name] = float(l[1])
		status = LpStatusUndefined # No status info
		return status, values

try:
	import pulpCOIN
	
	class COIN_MEM(LpSolver):
		"""The COIN LP solver (via a module)"""
		def __init__(self, mip = 1, msg = 1, cuts = 1, presolve = 1, dual = 1,
			crash = 0, scale = 1, rounding = 1, integerPresolve = 1, strong = 5):
			LpSolver.__init__(self, mip, msg)
			self.cuts = cuts
			self.presolve = presolve
			self.dual = dual
			self.crash = crash
			self.scale = scale
			self.rounding = rounding
			self.integerPresolve = integerPresolve
			self.strong = strong

		def copy(self):
			"""Make a copy of self"""
		
			aCopy = LpSolver.copy()
			aCopy.cuts = self.cuts
			aCopy.presolve = self.presolve
			aCopy.dual = self.dual
			aCopy.crash = self.crash
			aCopy.scale = self.scale
			aCopy.rounding = self.rounding
			aCopy.integerPresolve = self.integerPresolve
			aCopy.strong = self.strong
			return aCopy

		def available(self):
			"""True if the solver is available"""
			return True

		def actualSolve(self, lp):
			"""Solve a well formulated lp problem"""
			lp.status = pulpCOIN.solve(lp.objective, lp.constraints, lp.sense, 
				self.msg, self.mip, self.presolve, self.dual, self.crash, self.scale,
				self.rounding, self.integerPresolve, self.strong, self.cuts)
			return lp.status
	
	COIN = COIN_MEM
except:
	class COIN_MEM(LpSolver):
		"""The COIN LP solver (via a module)"""
		def available(self):
			"""True if the solver is available"""
			return False
		def actualSolve(self, lp):
			"""Solve a well formulated lp problem"""
			raise RuntimeError, "COIN_MEM: Not Available"

	COIN = COIN_CMD

# Default solver selection
if CPLEX_MEM().available():
	LpSolverDefault = CPLEX_MEM()
elif COIN_MEM().available():
	LpSolverDefault = COIN_MEM()
elif GLPK_MEM().available():
	LpSolverDefault = GLPK_MEM()
elif CPLEX_CMD().available():
	LpSolverDefault = CPLEX_CMD()
elif COIN_CMD().available():
	LpSolverDefault = COIN_CMD()
elif GLPK_CMD().available():
	LpSolverDefault = GLPK_CMD()
else:
	LpSolverDefault = None

class LpVariable:
	"""A LP variable"""
	def __init__(self, name, lowBound = None, upBound = None, cat = LpContinuous):
		self.name = ""
		for n in name:
			if n == "-" or n =="+":
				n = "_"
			self.name += n
		# self.hash MUST be different for each variable
		# else dict() will call the comparison operators that are overloaded
		self.hash = id(self)
		self.lowBound = lowBound
		self.upBound = upBound
		self.cat = cat
		self.varValue = None

	def matrix(self, name, indexs, lowBound = None, upBound = None, cat = 0, indexStart = []):
		if not isinstance(indexs, tuple): indexs = (indexs,)
		if "%" not in name:	name += "_%d" * len(indexs)

		index = indexs[0]
		indexs = indexs[1:]
		if len(indexs) == 0:
			return [LpVariable(name % tuple(indexStart + [i]), lowBound, upBound, cat) for i in index]
		else:
			return [LpVariable.matrix(name, indexs, lowBound, upBound, cat, indexStart + [i]) for i in index]
	matrix = classmethod(matrix)

	def dicts(self, name, indexs, lowBound = None, upBound = None, cat = 0, indexStart = []):
		if not isinstance(indexs, tuple): indexs = (indexs,)
		if "%" not in name:	name += "_%s" * len(indexs)

		index = indexs[0]
		indexs = indexs[1:]
		d = {}
		if len(indexs) == 0:
			for i in index:
				d[i] = LpVariable(name % tuple(indexStart + [str(i)]), lowBound, upBound, cat)
		else:
			for i in index:
				d[i] = LpVariable.dicts(name, indexs, lowBound, upBound, cat, indexStart + [i])
		return d
	dicts = classmethod(dicts)

	def dict(self, name, indexs, lowBound = None, upBound = None, cat = 0):
		if not isinstance(indexs, tuple): indexs = (indexs,)
		if "%" not in name:	name += "_%s" * len(indexs)

		lists = indexs

		if len(indexs)>1:
			# Cartesian product
			res = []
			while len(lists):
				first = lists[-1]
				nres = []
				if res:
					if first:
						for f in first:
							nres.extend([[f]+r for r in res])
					else:
						nres = res
					res = nres
				else:
					res = [[f] for f in first]
				lists = lists[:-1]
			index = [tuple(r) for r in res]
		elif len(indexs) == 1:
			index = indexs[0]
		else:
			return {}

		d = {}
		for i in index:
		 d[i] = self(name % i, lowBound, upBound, cat)
		return d
	dict = classmethod(dict)

	def bounds(self, low, up):
		self.lowBound = low
		self.upBound = up

	def positive(self):
		self.lowBound = 0
		self.upBound = None

	def value(self):
		return self.varValue
	
	def round(self, epsInt = 1e-5, eps = 1e-7):
		if self.varValue is not None:
			if self.upBound != None and self.varValue > self.upBound and self.varValue <= self.upBound + eps:
				self.varValue = self.upBound
			elif self.lowBound != None and self.varValue < self.lowBound and self.varValue >= self.lowBound - eps:
				self.varValue = self.lowBound
			if self.cat == LpInteger and abs(round(self.varValue) - self.varValue) <= epsInt:
				self.varValue = round(self.varValue)
	
	def roundedValue(self, eps = 1e-5):
		if self.cat == LpInteger and self.varValue != None \
			and abs(self.varValue - round(self.varValue)) <= eps:
			return round(self.varValue)
		else:
			return self.varValue
		
	def valueOrDefault(self):
		if self.varValue != None:
			return self.varValue
		elif self.lowBound != None:
			if self.upBound != None:
				if 0 >= self.lowBound and 0 <= self.upBound:
					return 0
				else:
					if self.lowBound >= 0:
						return self.lowBound
					else:
						return self.upBound
			else:
				if 0 >= self.lowBound:
					return 0
				else:
					return self.lowBound
		elif self.upBound != None:
			if 0 <= self.upBound:
				return 0
			else:
				return self.upBound
		else:
			return 0

	def valid(self, eps):
		if self.varValue == None: return False
		if self.upBound != None and self.varValue > self.upBound + eps:
			return False
		if self.lowBound != None and self.varValue < self.lowBound - eps:
			return False
		if self.cat == LpInteger and abs(round(self.varValue) - self.varValue) > eps:
			return False
		return True

	def infeasibilityGap(self, mip = 1):
		if self.varValue == None: raise ValueError, "variable value is None"
		if self.upBound != None and self.varValue > self.upBound:
			return self.varValue - self.upBound
		if self.lowBound != None and self.varValue < self.lowBound:
			return self.varValue - self.lowBound
		if mip and self.cat == LpInteger and round(self.varValue) - self.varValue != 0:
			return round(self.varValue) - self.varValue
		return 0

	def __hash__(self):
		return self.hash

	def __str__(self):
		return self.name

	def isBinary(self):
		return self.cat == LpInteger and self.lowBound == 0 and self.upBound == 1

	def isFree(self):
		return self.lowBound == None and self.upBound == None

	def isConstant(self):
		return self.lowBound != None and self.upBound == self.lowBound

	def isPositive(self):
		return self.lowBound == 0 and self.upBound == None

	def asCplexLpVariable(self):
		if self.isFree(): return self.name + " free"
		if self.isConstant(): return self.name + " = %.12g" % self.lowBound
		if self.lowBound == None:
			s= "-inf <= "
		# Note: XPRESS and CPLEX do not interpret integer variables without 
		# explicit bounds
		elif (self.lowBound == 0 and self.cat == LpContinuous):
			s = ""
		else:
			s= "%.12g <= " % self.lowBound
		s += self.name
		if self.upBound != None:
			s+= " <= %.12g" % self.upBound
		return s

	def asCplexLpAffineExpression(self, name, constant = 1):
		return LpAffineExpression(self).asCplexLpAffineExpression(name, constant)

	def __repr__(self):
		return self.name

	def __neg__(self):
		return - LpAffineExpression(self)
		
	def __pos__(self):
		return self

	def __nonzero__(self):
		return 1

	def __add__(self, other):
		return LpAffineExpression(self) + other

	def __radd__(self, other):
		return LpAffineExpression(self) + other
		
	def __sub__(self, other):
		return LpAffineExpression(self) - other
		
	def __rsub__(self, other):
		return other - LpAffineExpression(self)

	def __mul__(self, other):
		return LpAffineExpression(self) * other

	def __rmul__(self, other):
		return LpAffineExpression(self) * other
		
	def __div__(self, other):
		return LpAffineExpression(self)/other

	def __rdiv__(self, other):
		raise TypeError, "Expressions cannot be divided by a variable"

	def __le__(self, other):
		return LpAffineExpression(self) <= other

	def __ge__(self, other):
		return LpAffineExpression(self) >= other

	def __eq__(self, other):
		return LpAffineExpression(self) == other

	def __ne__(self, other):
		if isinstance(other, LpVariable):
			return self.name is not other.name
		elif isinstance(other, LpAffineExpression):
			if other.isAtomic():
				return self is not other.atom()
			else:
				return 1
		else:
			return 1

class LpAffineExpression(dict):
	"""A linear combination of LP variables"""
	def __init__(self, e = {}, constant = 0, name = None):
		self.name = name
		if isinstance(e,LpAffineExpression):
			# Will not copy the name
			self.constant = e.constant
			dict.__init__(self, e)
		elif isinstance(e,dict):
			self.constant = constant
			dict.__init__(self, e)
		elif isinstance(e,LpVariable):
			self.constant = 0
			dict.__init__(self, {e:1})
		else:
			self.constant = e
			dict.__init__(self)

	# Proxy functions for variables

	def isAtomic(self):
		return len(self) == 1 and self.constant == 0 and self.values()[0] == 1

	def isNumericalConstant(self):
		return len(self) == 0

	def atom(self):
		return self.keys()[0]

	# Functions on expressions

	def __nonzero__(self):
		return self.constant != 0 or len(self)

	def value(self):
		s = self.constant
		for v,x in self.iteritems():
			if v.varValue is None:
				return None
			s += v.varValue * x
		return s
		
	def valueOrDefault(self):
		s = self.constant
		for v,x in self.iteritems():
			s += v.valueOrDefault() * x
		return s
		
	def addterm(self, key, value):
			y = self.get(key, 0)
			if y:
				y += value
				if y: self[key] = y
				else: del self[key]
			else:
				self[key] = value

	def emptyCopy(self):
		return LpAffineExpression()
		
	def copy(self):
		"""Make a copy of self except the name which is reset"""
		# Will not copy the name
		return LpAffineExpression(self)
		
	def __str__(self, constant = 1):
		s = ""
		for v in self:
			val = self[v]
			if val<0:
				if s != "": s += " - "
				else: s += "-"
				val = -val
			elif s != "": s += " + "
			if val == 1: s += str(v)
			else: s += str(val) + "*" + str(v)
		if constant:
			if s == "":
				s = str(self.constant)
			else:
				if self.constant < 0: s += " - " + str(-self.constant)
				elif self.constant > 0: s += " + " + str(self.constant)
		elif s == "":
			s = "0"
		return s
		
	def __repr__(self):
		l = [str(self[v]) + "*" + str(v) for v in self]
		l.append(str(self.constant))
		s = " + ".join(l)
		return s

	def asCplexLpAffineExpression(self, name, constant = 1):
		# Ugly.
		s = ""
		sl = name + ":"
		notFirst = 0
		for v,val in self.iteritems():
			if val<0:
				ns = " - "
				val = -val
			elif notFirst:
				ns = " + "
			else:
				ns = " "
			notFirst = 1
			if val == 1: ns += v.name
			else: ns += "%.12g %s" % (val, v.name)
			if len(sl)+len(ns) > LpCplexLPLineSize:
				s += sl+"\n"
				sl = ns
			else:
				sl += ns
		if not self:
			ns = " " + str(self.constant)
		else:
			ns = ""
			if constant:
				if self.constant < 0: ns = " - " + str(-self.constant)
				elif self.constant > 0: ns = " + " + str(self.constant)
		if len(sl)+len(ns) > LpCplexLPLineSize:
			s += sl+"\n"+ns+"\n"
		else:
			s += sl+ns+"\n"
		return s

	def addInPlace(self, other):
		if other is 0: return self
		if isinstance(other,LpVariable):
			self.addterm(other, 1)
		elif isinstance(other,list):
			for e in other:
				self.addInPlace(e)
		elif isinstance(other,LpAffineExpression):
			self.constant += other.constant
			for v,x in other.iteritems():
				self.addterm(v, x)
		elif isinstance(other,dict):
			for e in other.itervalues():
				self.addInPlace(e)
		else:
			self.constant += other
		return self

	def subInPlace(self, other):
		if other is 0: return self
		if isinstance(other,LpVariable):
			self.addterm(other, -1)
		elif isinstance(other,list):
			for e in other:
				self.subInPlace(e)
		elif isinstance(other,LpAffineExpression):
			self.constant -= other.constant
			for v,x in other.iteritems():
				self.addterm(v, -x)
		elif isinstance(other,dict):
			for e in other.itervalues():
				self.subInPlace(e)
		else:
			self.constant -= other
		return self
		
	def __neg__(self):
		e = self.emptyCopy()
		e.constant = - self.constant
		for v,x in self.iteritems():
			e[v] = - x
		return e
		
	def __pos__(self):
		return self

	def __add__(self, other):
		return self.copy().addInPlace(other)

	def __radd__(self, other):
		return self.copy().addInPlace(other)
		
	def __sub__(self, other):
		return self.copy().subInPlace(other)
		
	def __rsub__(self, other):
		return (-self).addInPlace(other)

	def __mul__(self, other):
		e = self.emptyCopy()
		if isinstance(other,LpAffineExpression):
			e.constant = self.constant * other.constant
			if len(other):
				if len(self):
					raise TypeError, "Non-constant expressions cannot be multiplied"
				else:
					c = self.constant
					if c != 0:
						for v,x in other.iteritems():
							e[v] = c * x
			else:
				c = other.constant
				if c != 0:
					for v,x in self.iteritems():
						e[v] = c * x
		elif isinstance(other,LpVariable):
			return self * LpAffineExpression(other)
		else:
			if other != 0:
				e.constant = self.constant * other
				for v,x in self.iteritems():
					e[v] = other * x
		return e

	def __rmul__(self, other):
		return self * other
		
	def __div__(self, other):
		if isinstance(other,LpAffineExpression) or isinstance(other,LpVariable):
			if len(other):
				raise TypeError, "Expressions cannot be divided by a non-constant expression"
			other = other.constant
		e = self.emptyCopy()
		e.constant = self.constant / other
		for v,x in self.iteritems():
			e[v] = x / other
		return e

	def __rdiv__(self, other):
		e = self.emptyCopy()
		if len(self):
			raise TypeError, "Expressions cannot be divided by a non-constant expression"
		c = self.constant
		if isinstance(other,LpAffineExpression):
			e.constant = other.constant / c
			for v,x in other.iteritems():
				e[v] = x / c
		else:
			e.constant = other / c
		return e

	def __le__(self, other):
		return LpConstraint(self - other, LpConstraintLE)

	def __ge__(self, other):
		return LpConstraint(self - other, LpConstraintGE)

	def __eq__(self, other):
		return LpConstraint(self - other, LpConstraintEQ)

class LpConstraint(LpAffineExpression):
	"""An LP constraint"""
	def __init__(self, e = LpAffineExpression(), sense = LpConstraintEQ):
		LpAffineExpression.__init__(self, e)
		self.sense = sense

	def __str__(self):
		s = LpAffineExpression.__str__(self, 0)
		s += " " + LpConstraintSenses[self.sense] + " " + str(-self.constant)
		return s

	def asCplexLpConstraint(self, name):
		# Immonde.
		s = ""
		sl = name + ":"
		notFirst = 0
		for v,val in self.iteritems():
			if val<0:
				ns = " - "
				val = -val
			elif notFirst:
				ns = " + "
			else:
				ns = " "
			notFirst = 1
			if val == 1: ns += v.name
			else: ns += "%.12g %s" % (val , v.name)
			if len(sl)+len(ns) > LpCplexLPLineSize:
				s += sl+"\n"
				sl = ns
			else:
				sl += ns
		if not self: sl += "0"
		c = -self.constant
		if c == 0: c = 0 # Supress sign
		ns = " %s %.12g" % (LpConstraintSenses[self.sense], c)
		if len(sl)+len(ns) > LpCplexLPLineSize:
			s += sl + "\n" + ns + "\n"
		else:
			s += sl + ns + "\n"
		return s

	def __repr__(self):
		s = LpAffineExpression.__repr__(self)
		s += " " + LpConstraintSenses[self.sense] + " 0"
		return s
		
	def copy(self):
		"""Make a copy of self"""
		return LpConstraint(self, self.sense)
		
	def emptyCopy(self):
		return LpConstraint(sense = self.sense)

	def addInPlace(self, other):
		if isinstance(other,LpConstraint):
			if self.sense * other.sense >= 0:
				LpAffineExpression.addInPlace(self, other)	
				self.sense |= other.sense
			else:
				LpAffineExpression.subInPlace(self, other)	
				self.sense |= - other.sense
		elif isinstance(other,list):
			for e in other:
				self.addInPlace(e)
		else:
			raise TypeError, "Constraints and Expressions cannot be added"
		return self

	def subInPlace(self, other):
		if isinstance(other,LpConstraint):
			if self.sense * other.sense <= 0:
				LpAffineExpression.subInPlace(self, other)	
				self.sense |= - other.sense
			else:
				LpAffineExpression.addInPlace(self, other)	
				self.sense |= other.sense
		elif isinstance(other,list):
			for e in other:
				self.subInPlace(e)
		else:
			raise TypeError, "Constraints and Expressions cannot be added"
		return self
		
	def __neg__(self):
		c = LpAffineExpression.__neg__(self)
		c.sense = - c.sense
		return c

	def __add__(self, other):
		return self.copy().addInPlace(other)
		
	def __radd__(self, other):
		return self.copy().addInPlace(other)

	def __sub__(self, other):
		return self.copy().subInPlace(other)

	def __rsub__(self, other):
		return (-self).addInPlace(other)

	def __mul__(self, other):
		if isinstance(other,LpConstraint):
			c = LpAffineExpression.__mul__(self, other)
			if c.sense == 0:
				c.sense = other.sense
			elif other.sense != 0:
				c.sense *= other.sense
			return c
		else:
			return LpAffineExpression.__mul__(self, other)
		
	def __rmul__(self, other):
		return self * other

	def __div__(self, other):
		if isinstance(other,LpConstraint):
			c = LpAffineExpression.__div__(self, other)
			if c.sense == 0:
				c.sense = other.sense
			elif other.sense != 0:
				c.sense *= other.sense
			return c
		else:
			return LpAffineExpression.__mul__(self, other)

	def __rdiv__(self, other):
		if isinstance(other,LpConstraint):
			c = LpAffineExpression.__rdiv__(self, other)
			if c.sense == 0:
				c.sense = other.sense
			elif other.sense != 0:
				c.sense *= other.sense
			return c
		else:
			return LpAffineExpression.__mul__(self, other)

	def valid(self, eps = 0):
		val = self.value()
		if self.sense == LpConstraintEQ: return abs(val) <= eps
		else: return val * self.sense >= - eps

class LpProblem:
	"""An LP Problem"""
	def __init__(self, name = "NoName", sense = LpMinimize):
		self.objective = None
		self.constraints = {}
		self.name = name
		self.sense = sense
		self.sos1 = {}
		self.sos2 = {}
		self.status = LpStatusNotSolved
		self.noOverlap = 1
		
		# locals
		self.lastUnused = 0

	def __repr__(self):
		string = self.name+":\n"
		if self.sense == 1:
			string += "MINIMIZE\n"
		else:
			string += "MAXIMIZE\n"
		string += repr(self.objective) +"\n"

		if self.constraints:
			string += "SUBJECT TO\n"
			for n, c in self.constraints.iteritems():
				string += c.asCplexLpConstraint(n) +"\n"
		string += "VARIABLES\n"
		for v in self.variables():
			string += v.asCplexLpVariable() + " " + LpCategories[v.cat] + "\n"
		return string

	def copy(self):
		"""Make a copy of self. Expressions are copied by reference"""
		lpcopy = LpProblem(name = self.name, sense = self.sense)
		lpcopy.objective = self.objective
		lpcopy.constraints = self.constraints.copy()
		lpcopy.sos1 = self.sos1.copy()
		lpcopy.sos2 = self.sos2.copy()
		return lpcopy

	def deepcopy(self):
		"""Make a copy of self. Expressions are copied by value"""
		lpcopy = LpProblem(name = self.name, sense = self.sense)
		if lpcopy.objective != None:
			lpcopy.objective = self.objective.copy()
		lpcopy.constraints = {}
		for k,v in self.constraints.iteritems():
			lpcopy.constraints[k] = v.copy()
		lpcopy.sos1 = self.sos1.copy()
		lpcopy.sos2 = self.sos2.copy()
		return lpcopy

	def normalisedNames(self):
		constraintsNames = {}
		i = 0
		for k in self.constraints:
			constraintsNames[k] = "C%07d" % i
			i += 1
		variablesNames = {}
		i = 0
		for k in self.variables():
			variablesNames[k.name] = "X%07d" % i
			i += 1
		return constraintsNames, variablesNames, "OBJ"

	def isMIP(self):
		for v in self.variables():
			if v.cat == LpInteger: return 1
		return 0

	def roundSolution(self, epsInt = 1e-5, eps = 1e-7):
		for v in self.variables():
			v.round(epsInt, eps)

	def unusedConstraintName(self):
		self.lastUnused += 1
		while 1:
			s = "_C%d" % self.lastUnused
			if s not in self.constraints: break
			self.lastUnused += 1
		return s

	def valid(self, eps = 0):
		for v in self.variables():
			if not v.valid(eps): return False
		for c in self.constraints.itervalues():
			if not c.valid(eps): return False
		else:
			return True

	def infeasibilityGap(self, mip = 1):
		gap = 0
		for v in self.variables():
			gap = max(abs(v.infeasibilityGap(mip)), gap)
		for c in self.constraints.itervalues():
			if not c.valid(0):
				gap = max(abs(c.value()), gap)
		return gap

	def variables(self):
		variables = {}
		if self.objective:
			variables.update(self.objective)
		for c in self.constraints.itervalues():
			variables.update(c)
		return variables.keys()

	def variablesDict(self):
		variables = {}
		if self.objective:
			for v in self.objective:
				variables[v.name] = v
		for c in self.constraints.values():
			for v in c:
				variables[v.name] = v
		return variables
	
	def add(self, constraint, name = None):
		if not isinstance(constraint, LpConstraint):
			raise TypeError, "Can only add LpConstraint objects"
		if not name: name = constraint.name
		if not name: name = self.unusedConstraintName()
		self.constraints[name] = constraint
	
	def __iadd__(self, constraint):
		if isinstance(constraint, tuple):
			constraint, name = constraint
		else:
			name = None
		if constraint is True:
			return self
		if isinstance(constraint, LpConstraint):
			if not name:
				if constraint.name:
					name = constraint.name
				else:
					name = self.unusedConstraintName()
			if len(constraint) == 0:
				if not constraint.valid():
					raise ValueError, "Cannot add false constraints"
			else:
				if name in self.constraints:
					if self.noOverlap:
						raise "overlapping constraint names: " + name
					else:
						print "Warning: overlapping constraint names:", name
				self.constraints[name] = constraint
		elif isinstance(constraint, LpAffineExpression):
			self.objective = constraint
			self.objective.name = name
		elif isinstance(constraint, LpVariable) or type(constraint) in [int, float]:
			self.objective = LpAffineExpression(constraint)
			self.objective.name = name
		else:
			raise TypeError, "Can only add LpConstraint, LpAffineExpression or True objects"
		return self
	
	def extend(self, contraintes):
		if isinstance(contraintes, dict):
			for name in contraintes:
				self.constraints[name] = contraintes[name]
		else:
			for c in contraintes:
				if isinstance(c,tuple):
					name = c[0]
					c = c[1]
				else:
					name = None
				if not name: name = c.name
				if not name: name = self.unusedConstraintName()
				self.constraints[name] = c

	def coefficients(self, translation = None):
		coefs = []
		if translation == None:
			for c in self.constraints:
				cst = self.constraints[c]
				coefs.extend([(v.name, c, cst[v]) for v in cst])
		else:
			for c in self.constraints:
				ctr = translation[c]
				cst = self.constraints[c]
				coefs.extend([(translation[v.name], ctr, cst[v]) for v in cst])
		return coefs
		
	def writeMPS(self, filename, mpsSense = 0, rename = 0, mip = 1):
		wasNone, dummyVar = self.fixObjective()
		f = file(filename, "w")
		if mpsSense == 0: mpsSense = self.sense
		cobj = self.objective
		if mpsSense != self.sense:
			n = cobj.name
			cobj = - cobj
			cobj.name = n
		if rename:
			constraintsNames, variablesNames, cobj.name = self.normalisedNames()
		f.write("*SENSE:"+LpSenses[mpsSense]+"\n")
		n = self.name
		if rename: n = "MODEL"
		f.write("NAME          "+n+"\n")
		vs = self.variables()
		# constraints
		f.write("ROWS\n")
		objName = cobj.name
		if not objName: objName = "OBJ"
		f.write(" N  %s\n" % objName)
		mpsConstraintType = {LpConstraintLE:"L", LpConstraintEQ:"E", LpConstraintGE:"G"}
		for k,c in self.constraints.iteritems():
			if rename: k = constraintsNames[k]
			f.write(" "+mpsConstraintType[c.sense]+"  "+k+"\n")
		# matrix
		f.write("COLUMNS\n")
		# Creation of a dict of dict:
		# coefs[nomVariable][nomContrainte] = coefficient		
		coefs = {}
		for k,c in self.constraints.iteritems():
			if rename: k = constraintsNames[k]
			for v in c:
				n = v.name
				if rename: n = variablesNames[n]
				if n in coefs:
					coefs[n][k] = c[v]
				else:
					coefs[n] = {k:c[v]}
		
		for v in vs:
			if mip and v.cat == LpInteger:
				f.write("    MARK      'MARKER'                 'INTORG'\n")
			n = v.name
			if rename: n = variablesNames[n]
			if n in coefs:
				cv = coefs[n]
				# Most of the work is done here
				for k in cv: f.write("    %-8s  %-8s  % .5e\n" % (n,k,cv[k]))

			# objective function
			if v in cobj: f.write("    %-8s  %-8s  % .5e\n" % (n,objName,cobj[v]))
			if mip and v.cat == LpInteger:
				f.write("    MARK      'MARKER'                 'INTEND'\n")
		# right hand side
		f.write("RHS\n")
		for k,c in self.constraints.iteritems():
			c = -c.constant
			if rename: k = constraintsNames[k]
			if c == 0: c = 0
			f.write("    RHS       %-8s  % .5e\n" % (k,c))
		# bounds
		f.write("BOUNDS\n")
		for v in vs:
			n = v.name
			if rename: n = variablesNames[n]
			if v.lowBound != None and v.lowBound == v.upBound:
				f.write(" FX BND       %-8s  % .5e\n" % (n, v.lowBound))
			elif v.lowBound == 0 and v.upBound == 1 and mip and v.cat == LpInteger:
				f.write(" BV BND       %-8s\n" % n)
			else:
				if v.lowBound != None:
					# In MPS files, variables with no bounds (i.e. >= 0)
					# are assumed BV by COIN and CPLEX.
					# So we explicitly write a 0 lower bound in this case.
					if v.lowBound != 0 or (mip and v.cat == LpInteger and v.upBound == None):
						f.write(" LO BND       %-8s  % .5e\n" % (n, v.lowBound))
				else:
					if v.upBound != None:
						f.write(" MI BND       %-8s\n" % n)
					else:
						f.write(" FR BND       %-8s\n" % n)
				if v.upBound != None:
					f.write(" UP BND       %-8s  % .5e\n" % (n, v.upBound))
		f.write("ENDATA\n")
		f.close()
		self.restoreObjective(wasNone, dummyVar)
		# returns the variables, in writting order
		if rename == 0:
			return vs
		else:
			return vs, variablesNames, constraintsNames, cobj.name
		
	def writeLP(self, filename, writeSOS = 1, mip = 1):
		f = file(filename, "w")
		f.write("\\* "+self.name+" *\\\n")
		if self.sense == 1:
			f.write("Minimize\n")
		else:
			f.write("Maximize\n")
		wasNone, dummyVar = self.fixObjective()
		objName = self.objective.name
		if not objName: objName = "OBJ"
		f.write(self.objective.asCplexLpAffineExpression(objName, constant = 0))
		f.write("Subject To\n")
		ks = self.constraints.keys()
		ks.sort()
		for k in ks:
			f.write(self.constraints[k].asCplexLpConstraint(k))
		vs = self.variables()
		vs.sort()
		# Bounds on non-"positive" variables
		# Note: XPRESS and CPLEX do not interpret integer variables without 
		# explicit bounds
		if mip:
			vg = [v for v in vs if not (v.isPositive() and v.cat == LpContinuous) \
				and not v.isBinary()]
		else:
			vg = [v for v in vs if not v.isPositive()]
		if vg:
			f.write("Bounds\n")
			for v in vg:
				f.write("%s\n" % v.asCplexLpVariable())
		# Integer non-binary variables
		if mip:
			vg = [v for v in vs if v.cat == LpInteger and not v.isBinary()]
			if vg:
				f.write("Generals\n")
				for v in vg: f.write("%s\n" % v.name)
			# Binary variables
			vg = [v for v in vs if v.isBinary()]
			if vg:
				f.write("Binaries\n")
				for v in vg: f.write("%s\n" % v.name)
		# Special Ordered Sets
		if writeSOS and (self.sos1 or self.sos2):
			f.write("SOS\n")
			if self.sos1:
				for sos in self.sos1.itervalues():
					f.write("S1:: \n")
					for v,val in sos.iteritems():
						f.write(" %s: %.12g\n" % (v.name, val))
			if self.sos2:
				for sos in self.sos2.itervalues():
					f.write("S2:: \n")
					for v,val in sos.iteritems():
						f.write(" %s: %.12g\n" % (v.name, val))
		f.write("End\n")
		f.close()
		self.restoreObjective(wasNone, dummyVar)
		
	def assign(self, values):
		variables = self.variablesDict()
		for name in values:
			variables[name].varValue = values[name]

	def fixObjective(self):
		if self.objective is None:
			self.objective = 0
			wasNone = 1
		else:
			wasNone = 0
		if not isinstance(self.objective, LpAffineExpression):
			self.objective = LpAffineExpression(self.objective)
		if self.objective.isNumericalConstant():
			dummyVar = LpVariable("__dummy", 0, 0)
			self.objective += dummyVar
		else:
			dummyVar = None
		return wasNone, dummyVar

	def restoreObjective(self, wasNone, dummyVar):
		if wasNone:
			self.objective = None
		elif not dummyVar is None:
			self.objective -= dummyVar

	def solve(self, solver = LpSolverDefault):
		wasNone, dummyVar = self.fixObjective()
		status = solver.actualSolve(self)
		self.restoreObjective(wasNone, dummyVar)
		return status

class LpVariableDict(dict):
	"""An LP variable generator"""
	def __init__(self, name, data = {}, lowBound = None, upBound = None, cat = 0):
		self.name = name
		dict.__init__(self, data)
		
	def __getitem__(self, key):
		if key in self:
			return dict.__getitem__(self, key)
		else:
			self[key] = LpVariable(name % key, lowBound, upBound, cat)
			return self[key]

# Utility fonctions

def lpSum(vector):
	"""Calculate the sum of a list of linear expressions"""
	return LpAffineExpression().addInPlace(vector)

def lpDot(v1, v2):
	"""Calculate the dot product of two lists of linear expressions"""
	if not isinstance(v1, list) and not isinstance(v2, list):
		return v1 * v2
	elif not isinstance(v1, list):
		return lpDot([v1]*len(v2),v2)
	elif not isinstance(v2, list):
		return lpDot(v1,[v2]*len(v1))
	else:
		return lpSum([lpDot(e1,e2) for e1,e2 in zip(v1,v2)])

def isNumber(x):
	"""Returns true if x is an int of a float"""
	return type(x) in [int, float]

def value(x):
	"""Returns the value of the variable/expression x, or x if it is a number"""
	if isNumber(x): return x
	else: return x.value()

def valueOrDefault(x):
	"""Returns the value of the variable/expression x, or x if it is a number
	Variable wihout value (None) are affected a possible value (within their 
	bounds)."""
	if isNumber(x): return x
	else: return x.valueOrDefault()

# Tests

def pulpTestCheck(prob, solver, okstatus, sol = {}):
	status = prob.solve(solver)
	if status not in okstatus:
		prob.writeLP("debug.lp")
		prob.writeMPS("debug.mps")
		print "Failure: status ==", status, "not in", okstatus
		raise "Tests failed for solver ", solver
	if sol:
		for v,x in sol.iteritems():
			if v.varValue != x:
				prob.writeLP("debug.lp")
				prob.writeMPS("debug.mps")
				print "Test failed: var", v, "==", v.varValue, "!=", x
				raise "Tests failed for solver ", solver

def pulpTest1(solver):
	# Continuous
	prob = LpProblem("test1", LpMinimize)
	x = LpVariable("x", 0, 4)
	y = LpVariable("y", -1, 1)
	z = LpVariable("z", 0)
	w = LpVariable("w", 0)
	prob += x + 4*y + 9*z, "obj"
	prob += x+y <= 5, "c1"
	prob += x+z >= 10, "c2"
	prob += -y+z == 7, "c3"
	prob += w >= 0, "c4"
	pulpTestCheck(prob, solver, [LpStatusOptimal], {x:4, y:-1, z:6, w:0})

def pulpTest2(solver):
	# MIP
	prob = LpProblem("test2", LpMinimize)
	x = LpVariable("x", 0, 4)
	y = LpVariable("y", -1, 1)
	z = LpVariable("z", 0, None, LpInteger)
	prob += x + 4*y + 9*z, "obj"
	prob += x+y <= 5, "c1"
	prob += x+z >= 10, "c2"
	prob += -y+z == 7.5, "c3"
	if solver.__class__ is COIN_CMD:
		# COIN_CMD always return LpStatusUndefined for MIP problems
		pulpTestCheck(prob, solver, [LpStatusUndefined], {x:3, y:-0.5, z:7})
	else:
		pulpTestCheck(prob, solver, [LpStatusOptimal], {x:3, y:-0.5, z:7})

def pulpTest3(solver):
	# relaxed MIP
	prob = LpProblem("test3", LpMinimize)
	x = LpVariable("x", 0, 4)
	y = LpVariable("y", -1, 1)
	z = LpVariable("z", 0, None, LpInteger)
	prob += x + 4*y + 9*z, "obj"
	prob += x+y <= 5, "c1"
	prob += x+z >= 10, "c2"
	prob += -y+z == 7.5, "c3"
	solver.mip = 0
	pulpTestCheck(prob, solver, [LpStatusOptimal], {x:3.5, y:-1, z:6.5})

def pulpTest4(solver):
	# Feasibility only
	prob = LpProblem("test4", LpMinimize)
	x = LpVariable("x", 0, 4)
	y = LpVariable("y", -1, 1)
	z = LpVariable("z", 0, None, LpInteger)
	prob += x+y <= 5, "c1"
	prob += x+z >= 10, "c2"
	prob += -y+z == 7.5, "c3"
	if solver.__class__ is COIN_CMD:
		# COIN_CMD always return LpStatusUndefined
		pulpTestCheck(prob, solver, [LpStatusUndefined])
		if x.varValue is None or x.varValue is None or x.varValue is None:
			raise "Tests failed for solver ", solver
	else:
		pulpTestCheck(prob, solver, [LpStatusOptimal])

def pulpTest5(solver):
	# Infeasible
	prob = LpProblem("test5", LpMinimize)
	x = LpVariable("x", 0, 4)
	y = LpVariable("y", -1, 1)
	z = LpVariable("z", 0, 10)
	prob += x+y <= 5.2, "c1"
	prob += x+z >= 10.3, "c2"
	prob += -y+z == 17.5, "c3"
	if solver.__class__ is GLPK_CMD:
		# GLPK_CMD return codes are not enough informative
		pulpTestCheck(prob, solver, [LpStatusUndefined])
	elif solver.__class__ is CPLEX_MEM:
		# CPLEX_MEM returns InfeasibleOrUnbounded
		pulpTestCheck(prob, solver, [LpStatusInfeasible, LpStatusUndefined])
	else:
		pulpTestCheck(prob, solver, [LpStatusInfeasible])

def pulpTest6(solver):
	# Integer Infeasible
	prob = LpProblem("test6", LpMinimize)
	x = LpVariable("x", 0, 4, LpInteger)
	y = LpVariable("y", -1, 1, LpInteger)
	z = LpVariable("z", 0, 10, LpInteger)
	prob += x+y <= 5.2, "c1"
	prob += x+z >= 10.3, "c2"
	prob += -y+z == 7.4, "c3"
	if solver.__class__ in [GLPK_MEM, GLPK_CMD, COIN_CMD]:
		# GLPK_CMD return codes are not enough informative
		# GLPK_MEM integer return codes seems wrong
		# COIN_CMD integer return code is always LpStatusUndefined
		pulpTestCheck(prob, solver, [LpStatusUndefined])
	elif solver.__class__ is CPLEX_MEM:
		# CPLEX_MEM returns InfeasibleOrUnbounded
		pulpTestCheck(prob, solver, [LpStatusInfeasible, LpStatusUndefined])
	else:
		pulpTestCheck(prob, solver, [LpStatusInfeasible])

def pulpTestSolver(solver):
	tests = [pulpTest1, pulpTest2, pulpTest3, pulpTest4,
		pulpTest5, pulpTest6]
	for t in tests:
		t(solver(msg=0))

def pulpTestAll():
	solvers = [COIN_MEM, COIN_CMD, 
		CPLEX_MEM, CPLEX_CMD,
		GLPK_MEM, GLPK_CMD,
		XPRESS]
	
	for s in solvers:
		if s().available():
			pulpTestSolver(s)
			print "* Solver", s, "passed."
		else:
			print "Solver", s, "unavailable."

if __name__ == '__main__':
	# Tests
	pulpTestAll()
