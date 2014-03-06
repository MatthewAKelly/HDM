import ccm
from ccm.lib.actr import *

log=ccm.log(html=True)


class Addition(ACTR):
  goal=Buffer()
  retrieve=Buffer()
  memory=HDM(retrieve)
  
  def init():
    memory.add('do:count from:0 to:1')
    memory.add('do:count from:1 to:2')
    memory.add('do:count from:2 to:3')
    memory.add('do:count from:3 to:4')
    memory.add('do:count from:4 to:5')
    memory.add('do:count from:5 to:6')
    memory.add('do:count from:6 to:7')
    memory.add('do:count from:7 to:8')

  def initializeAddition(goal='add ?num1 ?num2 count:None?count sum:None?sum'):
    goal.modify(count=0,sum=num1)
    memory.request('do:count from:?num1 to:?next')

  def terminateAddition(goal='add ?num1 ?num2 count:?num2 sum:?sum'):
    goal.set('result ?sum')
    print sum

  def incrementSum(goal='add ?num1 ?num2 count:?count!?num2 sum:?sum',
                   retrieve='do:count from:?sum to:?next'):
    goal.modify(sum=next)
    memory.request('do:count from:?count to:?n2')

  def incrementCount(goal='add ?num1 ?num2 count:?count sum:?sum',
                     retrieve='do:count from:?count to:?next'):
    goal.modify(count=next)
    memory.request('do:count from:?sum to:?n2')


model=Addition()
ccm.log_everything(model)
model.goal.set('add 5 2 count:None sum:None')
model.run()



