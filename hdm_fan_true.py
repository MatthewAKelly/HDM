import ccm
from ccm.lib.actr import *
from ccm.lib.actr.hdm import *
log=ccm.log(html=True)

class FanModel(ACTR):
  goal=Buffer()
  retrieval=Buffer()
  memory=HDM(retrieval,latency=0.63)
  
  def init():
    backgroundPerItem = 10 # amount of background knowledge the modelled subject has for each item
    # (realistically this might vary with the word frequency of each word)
    
    # background knowledge
    places = ('park','church','bank','cave','beach','castle','dungeon','forest','store')
    people = ('hippie','captain','debutante','fireman','giant','earl','lawyer')
    for person in people:
        for x in range(1,backgroundPerItem+1): #range from (x,y) includes x but not y
            memory.add(person + ' in ' + str(x) + ' no')
    for place in places:
        for x in range(-1*(backgroundPerItem+1),0): # negative numbers are places
            memory.add(str(x) + ' in ' + place + ' no')
            
    # experimental study set
    memory.add('hippie in park yes')
    memory.add('hippie in church yes')    
    memory.add('hippie in bank yes')    
    memory.add('captain in park yes')    
    memory.add('captain in cave yes')    
    memory.add('debutante in bank yes')    
    memory.add('fireman in park yes')    
    memory.add('giant in beach yes')    
    memory.add('giant in castle yes')    
    memory.add('giant in dungeon yes')    
    memory.add('earl in castle yes')    
    memory.add('earl in forest yes')    
    memory.add('lawyer in store yes')
    
  def start(goal='test ?person ?location'):
    memory.request('?person in ?location ?')
    goal.set('recall ?person ?location')
    
  def respond_yes(goal='recall ?person ?location',
                  retrieval='?person in ?location yes'):
    print 'yes'
    goal.clear()

  def respond_no(goal='recall ?person ?location',
                        retrieval='?person in ?location no'):
    print 'no'
    goal.clear()


model=FanModel()
ccm.log_everything(model)
model.goal.set('test hippie park')
model.run()