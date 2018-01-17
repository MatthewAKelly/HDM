#################### ham cheese forgetting DM model ###################

# this model turns on the subsymbolic processing for DM, which causes forgetting


import ccm      
log=ccm.log()   

from ccm.lib.actr import *  
from ccm.lib.hrr import HRR

#####
# Python ACT-R requires an environment
# but in this case we will not be using anything in the environment
# so we 'pass' on putting things in there

class MyEnvironment(ccm.Model):
    display     = ccm.Model(word="START")
    
    # start presenting the list
    def start_list(self):
        times = [0.7090, 3.8111, 6.9672, 9.8382, 18.2230, 18.7200, 19.0000, 24.0890, 29.4293, 29.9843]
        print self.now()
        stimulus = "TEST"
        for time in times:
            yield max(time - self.now(),0)
            self.display.word = stimulus
        yield 30 - self.now()
        self.display.word = "OFF"

#####
# create an act-r agent

class MyAgent(ACTR):
    DMbuffer=Buffer()                   

    Use_HDM = True
    
    if Use_HDM: # standard latency = 0.05
        DM=HDM(DMbuffer,N=64,latency=0.5,verbose=False,noise=1.0,forgetting=0.9)
    else: # standard latency = 0.05
        DM=Memory(DMbuffer,latency=0.5,threshold=0)            
        dm_n=DMNoise(DM,noise=0.0,baseNoise=0.0)         # turn on for DM subsymbolic processing
        dm_bl=DMBaseLevel(DM,decay=0.5,limit=None)       # turn on for DM subsymbolic processing

    # STUDY THE TEST ITEM
    
    def start(display='word:START'):
        self.parent.start_list()

    def add(display='word:TEST'):
        DM.add('test item')
        self.parent.display.word = 'NONE'

print "Begin simulation"

tim=MyAgent()                              # name the agent
subway=MyEnvironment()                     # name the environment
subway.agent=tim                           # put the agent in the environment

ccm.log_everything(subway)                 # print out what happens in the environment
log=ccm.log(html=True)

times = []
activation = []

print "Run ACT-R"

#for i in range(0,300):
while subway.display.word != "OFF":
    subway.run(limit=0.1)   # run simulation for 100ms
    times.append(subway.now())
    try:
        a = subway.agent.DM.get_activation('test item')
    except:
        a = 0.0
    activation.append(a)
ccm.finished()                             # stop the environment

if subway.agent.Use_HDM:
    # write the activations to a file
    HDMfile = open('memory_activations_Hdm_d=64_f=9_n=1.txt', 'w')
    for a in activation:
        HDMfile.write("%s \n" % a)
else:  
    DMfile = open('memory_activations_dm.txt', 'w')
    for a in activation:
        DMfile.write("%s \n" % a)
