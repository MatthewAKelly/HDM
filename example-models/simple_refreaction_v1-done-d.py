#################### ham cheese forgetting DM model ###################
 
import ccm      
log=ccm.log(html=True)  
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
            
    DM=HDM(DMbuffer,latency=0.05,threshold=-25,maximum_time=20,finst_size=10,finst_time=30.0,verbose=True)     
                                                    # turn down threshold
                                                    # maximum time - how long it will wait for a memory retrieval
                                                    # finst_size - how many chunks can be kept track of
                                                    # finst_time - how long a chunk can be kept track of

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

    # note that this model uses slot names - slotname:slotcontent
    def init():
        print "Memorizing the customer orders"
        DM.add('isa:order customer:customer1 type:ham_cheese condiment:mustard')         # customer1's order
        DM.add('isa:order customer:customer2 type:ham_cheese condiment:ketchup')         # customer2's order
        DM.add('isa:order customer:customer3 type:ham_cheese condiment:mayonnaise')      # customer3's order
        DM.add('isa:order customer:customer4 type:ham_cheese condiment:hot_sauce')       # customer4's order
        focus.set('isa:ingrediant type:bread')
        
    def bread_bottom(focus='isa:ingrediant type:bread'):   
        print "I have a piece of bread"
        focus.set('isa:ingrediant type:cheese')
        
    def cheese(focus='isa:ingrediant type:cheese'):        
        print "I have put cheese on the bread"  
        focus.set('isa:ingrediant type:ham')
        
    def ham(focus='isa:ingrediant type:ham'):
        print "I have put  ham on the cheese"
        focus.set('isa:order customer:customer1 type:ham_cheese condiment:unknown')         
                                        
    def condiment(focus='isa:order customer:customer1 type:ham_cheese condiment:unknown'):
        print "recalling the order"     
        DM.request('isa:order type:ham_cheese condiment:?',require_new=True) # retrieve something that has not recently been retrieved           
        focus.set('retrieve_condiment')
        
    def order(focus='retrieve_condiment', DMbuffer='isa:order type:ham_cheese condiment:?condiment_order'): 
        print "I recall they wanted......."         
        print condiment_order            
        print "i have put the condiment on the sandwich"
        focus.set('isa:ingrediant type:bread_top')
        
    def bread_top(focus='isa:ingrediant type:bread_top'):
        print "I have put bread on the ham"
        print "I have made a ham and cheese sandwich"
        focus.set('isa:ingrediant type:bread')
        DMbuffer.clear()                        # clear the buffer for the next cycle


tim=MyAgent()                              # name the agent
subway=MyEnvironment()                     # name the environment
subway.agent=tim                           # put the agent in the environment
ccm.log_everything(subway)                 # print out what happens in the environment
subway.run(10)                              # run the environment
ccm.finished()                             # stop the environment
