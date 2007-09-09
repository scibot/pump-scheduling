# Pump scheduling in pulp/python.
# Author: Luigi Poderico
# www.poderico.it
###########################################################

from pulp import *

## Data ##

numPumps = 32
pumpSet = range(numPumps)
numTimes = 24
timeSet = range(numTimes)

## Energy consumpio for each pump
energyForPump = [0, 595, 260, 855, 260, 855, 520, 1115, 445, 1040, 705,
                 1300, 705, 1300, 965, 1560, 595, 1190, 855, 1450, 855,
                 1450, 1115, 1710, 1040, 1635, 1300, 1895, 1300, 1895,
                 1560, 2155]
assert (len(energyForPump) == numPumps)

## Discharge for each pump
dischargeForPump = [0, 1800, 828, 2600, 828, 2600, 1650, 3450, 1440, 3235,
                    2260, 4060, 2260, 4060, 3090, 4890, 1800, 3600, 2620,
                    4420, 2620, 4420, 3450, 5250, 3235, 5035, 4060, 5860,
                    4060, 5860, 4890, 6690]
assert (len(dischargeForPump) == numPumps)


## Cost on time
energyCost = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
              100, 100, 100, 100, 100, 200, 200, 200, 200, 200, 100, 100]
assert (len(energyCost) == numTimes)

## Pump status history
pumpHistory = 0
assert (0<=pumpHistory<numPumps)

## Water demand
waterDemand = [1.92, 1.55, 1.55, 1.55, 1.92, 2.73, 3.91, 5.03, 5.84, 6.22,
               6.22, 6.22, 5.47, 5.47, 5.84, 5.84, 5.84, 5.47, 5.03, 4.28,
               3.91, 3.10, 2.73, 2.36]
assert (len(waterDemand) == numTimes)
totalDemand = 10000
print "WaterDemand",
for i in range(numTimes):
    waterDemand[i] = totalDemand / 100 * waterDemand[i]
    print waterDemand[i],
    pass
print

## Reservoure min and max volume
minVolume = 1 * 2600
maxVolume = 7 * 2600
initVolume = 3 * 2600

## Variables ##

## Pump status
pumpStatus = LpVariable.matrix("pumpStatus", (pumpSet, timeSet), 0, 1, LpInteger)

## Volumes
volumes = LpVariable.matrix("volumes", (timeSet), minVolume, maxVolume)

## Slack variables for volumes
volumesSPlus = LpVariable.matrix("volumesSPlus", (timeSet), 0, maxVolume)
volumesSMinus = LpVariable.matrix("volumesSMinus", (timeSet), 0, maxVolume)


## Model ##
prob = LpProblem("test1", LpMinimize)

## Constraints ##

## One pump at time
for t in timeSet:
    prob += lpSum( [pumpStatus[i][t] for i in pumpSet]) == 1
    pass

## Flow conservation
for t in range(1,numTimes):
    prob += volumes[t] == volumes[t-1] - waterDemand[t] + \
            lpSum( [pumpStatus[i][t] * dischargeForPump[i] for i in pumpSet])
    pass
prob += volumes[0] == initVolume - waterDemand[0] + \
        lpSum( [pumpStatus[i][0] * dischargeForPump[i] for i in pumpSet])

## Volume slack variables
##for t in range(1, numTimes):
for t in range(1, numTimes):
    prob += volumes[t-1] - volumes[t] == volumesSPlus[t] - volumesSMinus[t]
    pass
prob += initVolume - volumes[0] == volumesSPlus[0] - volumesSMinus[0]

## Objective functions ##

## Cost energy
costEnergy = \
           lpSum ( [ \
               lpSum ( [ energyForPump[i]*energyCost[t]*pumpStatus[i][t] \
                         for i in pumpSet ] ) \
            for t in timeSet  ] )
            
## Level variation
levelVariation = lpSum ( [ volumesSPlus[t] + volumesSMinus[t] for t in timeSet ] )


## Solving problems ##
##myOptions = ["--tmlim 120", "--nomip"]
##solver = GLPK(path = "C:\\usr\\bin\\glpsol.exe", keepFiles = 1, msg = 1, options = myOptions)

myOptions = ["sec 90"]
solver = COIN(path = ["C:\\usr\\bin\\cbc.exe", "C:\\usr\\bin\\cbc.exe"], keepFiles = 1, msg = 1, options = myOptions)

##prob += costEnergy
prob += levelVariation
status = solver.solve(prob)


### Functions ###
def calcCost():
    myCost = 0

    for t in timeSet:
        for i in pumpSet:
            myCost += value(pumpStatus[i][t]) * energyForPump[i] * energyCost[t]
            pass
        pass
    
    return myCost


### Output ###

print "Volume", 
for t in timeSet:
    print value(volumes[t]),
    pass
print

print "Discharge", 
for t in timeSet:
    for i in pumpSet:
        if value(pumpStatus[i][t])==1:
            print value(dischargeForPump[i]),
            break
        pass
    pass
print

print "Pumping", 
for t in timeSet:
    for i in pumpSet:
        if value(pumpStatus[i][t])==1:
            print i,
            break
        pass
    pass
print

print "delta_volumes_+", 
for t in timeSet:
    print value(volumesSPlus[t]),
    pass
print

print "delta_volumes_-", 
for t in timeSet:
    print value(volumesSMinus[t]),
    pass
print

myCost = calcCost()
print "Cost:", myCost

print "Status: ", status
print "objective=", value(prob.objective)





            