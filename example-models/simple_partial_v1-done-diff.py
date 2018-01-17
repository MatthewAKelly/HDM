#################### ham cheese forgetting DM model ###################



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

    # turn on some noise and forgetting to allow errors
    DM=HDM(DMbuffer,latency=0.05,threshold=-1,noise=1.0,forgetting=0.5,verbose=True)     
        
    # set the similarity between customers
    # DM.get gets the environment vector for a given feature
    #   (and creates it if it is not already defined)
    # DM.set is a function for setting the environment vector to a specified vector
    #   (and normalizes the vectors to Euclidean length of one)
    # customers 1 and 2 are very similar
    # customers 1 and 3 are not so similar
    DM.set('customer1', DM.get('moustache')  + DM.get('blond') + DM.get('long_hair')  + DM.get('white'))
    DM.set('customer2', DM.get('moustache')  + DM.get('blond') + DM.get('short_hair') + DM.get('white')) 
    DM.set('customer3',                   DM.get('black_hair') + DM.get('long_hair')  + DM.get('East_Asian'))
                                                        
    def init():
        DM.add('customer:customer1 condiment:mustard')         # customer1's order
        DM.add('customer:customer2 condiment:ketchup')         # customer2's order
        DM.add('customer:customer3 condiment:mayonnaise')      # customer3's order
        focus.set('sandwich bread')
        
    def bread_bottom(focus='sandwich bread'):   
        print "I have a piece of bread"
        focus.set('sandwich cheese')    

    def cheese(focus='sandwich cheese'):        
        print "I have put cheese on the bread"  
        focus.set('sandwich ham')

    def ham(focus='sandwich ham'):
        print "I have put  ham on the cheese"
        focus.set('customer1 condiment')         
                                        
    def condiment(focus='customer1 condiment'):  # customer1 will spread activation to 'customer1 mustard'
        print "recalling the order"              # but also some to 'customer2 ketchup' and less to 'customer3 mayonaise'
        DM.request('customer:customer1 condiment:?condiment')               
        focus.set('sandwich condiment') 

    def order(focus='sandwich condiment', DMbuffer='customer:? condiment:?condiment'):  
        print "I recall they wanted......."         
        print condiment             
        print "i have put the condiment on the sandwich"
        focus.set('sandwich bread_top')

    def forgot(focus='sandwich condiment', DMbuffer=None, DM='error:True'):
        print "I recall they wanted......."
        print "I forgot"
        focus.set('stop')

    def bread_top(focus='sandwich bread_top'):
        print "I have put bread on the ham"
        print "I have made a ham and cheese sandwich"
        focus.set('stop')               

    def stop_production(focus='stop'):
        self.stop()

tim=MyAgent()                              # name the agent
subway=MyEnvironment()                     # name the environment
subway.agent=tim                           # put the agent in the environment
ccm.log_everything(subway)                 # print out what happens in the environment

subway.run()                               # run the environment
ccm.finished()                             # stop the environment
