#################### ham cheese forgetting DM model ###################

# this model turns on the subsymbolic processing for DM, which causes forgetting


import ccm      
log=ccm.log()   

from ccm.lib.actr import *  
from ccm.lib.actr.hdm import *
#####
# Python ACT-R requires an environment
# but in this case we will not be using anything in the environment
# so we 'pass' on putting things in there

class MyEnvironment(ccm.Model):
    pass

#####
# create an act-r agent

class MyAgent(ACTR):
    focus=Buffer()

    DMbuffer=Buffer()      
    # latency controls the relationship between activation and recall                                                        
    # activation must be above threshold - can be set to none
    # forgetting is the forgetting rate, 1 is perfect recall, 0 is no recall
    # noise is the amount of noise, 0 is no noise
    DM=HDM(DMbuffer,latency=1.0,threshold=1,verbose=True,forgetting=0.4,noise=5.0)   

    def init():
        DM.add('customer:customer1 condiment:mustard')
        focus.set('rehearse')
                                        
    def request_chunk(focus='rehearse'):  
        print "recalling the order"
        DM.request('customer:customer1 condiment:?condiment')            
        focus.set('recall') 

    def recall_chunk(focus='recall', DMbuffer='customer:customer1 condiment:?condiment'):  
        print "Customer 1 wants......."         
        print condiment                     # note - outside the quotes you do not need the ?       
        DM.add('customer:customer1 condiment:?condiment')      # but inside you do   
        DMbuffer.clear()                    # each time you put something in memory (DM.add) it increases activation
        focus.set('rehearse')

    def forgot(focus='recall', DMbuffer=None, DM='error:True'):
                                           # DMbuffer=none means the buffer is empty
                                           # DM='error:True' means the search was unsucessful
        print "I recall they wanted......."
        print "I forgot"
        focus.set('stop')



tim=MyAgent()                              # name the agent
subway=MyEnvironment()                     # name the environment
subway.agent=tim                           # put the agent in the environment
ccm.log_everything(subway)                 # print out what happens in the environment
log=ccm.log(html=True)
subway.run(2)                               # run the environment FOR 2 SECONDS
ccm.finished()                             # stop the environment
