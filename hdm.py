# HDM: Holographic Declarative Memory
# A module for Python ACT-R
# written by Matthew A. Kelly
# except for the parts written by Terry Stewart
# Based on original research and the memory models
# BEAGLE (Jones & Mewhort, 2007) and DSHM (Rutledge-Taylor, Kelly, West, & Pyke, 2014)
#
# To use HDM:
#   from ccm.lib.actr import *
#   from ccm.lib.actr.hdm import *
# ...
#   retrieval=Buffer()
#   memory=HDM(retrieval)
#
# HDM has some unique parameters that DM does not have:
#   N is the dimensionality of the vectors. 
#       Defaults to a generous 512 dimensions. 
#       As few as 64 and as many as 2048 have been used in the literature 
#       depending on the amount of noise or clarity desired.
#   verbose defaults to False
#       set to True if you want to see what HDM is doing in detail
# HDM also has some parameters that DM has and that are still important:   
#   buffer is the buffer used to output chunks retrieved from HDM
#   latency is F in Fe^-a, where a is the activation calculated as 
#   a = ln(cosine^2 / (1 - cosine^2))
#
# HDM has three important functions to call:
# add(chunk): adds a chunk to memory
# request(chunk): 
#       1. Given a chunk with exactly one unknown value '?', 
#       request finds the best value to fill '?'
#       which it returns
#       Reaction time is a function of cosine (similarity of chunk to memory)
#
#       2. Given a chunk with no unknown values,
#       resonance will return the chunk if it is familiar 
#       or fail to return the chunk if it is unfamiliar
#       i.e., has a cosine less than threshold
#       Reaction time is a function of cosine (similarity of chunk to memory)
# get_activation(chunk):
#       Computes the coherence of a chunk, which used in request type 2.
#       Returns a mean cosine.

from __future__ import generators
import ccm
import math
import numpy
import copy

__all__=['HDM']

from ccm.lib.actr.buffer import Chunk,Buffer
# add for hdm
from ccm.lib.actr.dm import Memory
from ccm.pattern import Pattern
from ccm.lib.hrr import HRR

class HDM(Memory):
  # buffer is the buffer that the retrieved chunk is placed in
  # N is the vector dimensionality
  #     recommended dimensionality in the range of 512 to 2048, defaults to 512
  #     a smaller dimensionality than 512 can be used to introduce additional noise
  # threshold is the lowest log odds activation allowed for a response
  #     this value is converted to a cosine similarity
  #     if no memory vector has a similarity to the query greater than threshold, the retrieval fails
  # maximum time is the most time the memory system is allowed to take
  # latency is used to calculate reaction time
  #     reaction time = latency * e^(-cosine)
  #     Note that using this equation, given a cosine of 0, the reaction time = latency
  #     Bigger latencies result in longer reaction times
  # verbose defaults to FALSE. 
  #     If TRUE, verbose turns on print statements giving details about what HDM is doing.
  # forgetting controls the forgetting rate due to retroactive inhibition
  #     range [0 to 1]
  #     1 = no forgetting
  #     0 = no remembering
  #     When updating memory:
  #     memory vector =  forgetting * memory vector + new information vector
  # noise controls the amount of noise added to memory per time step
  #     Gaussian noise is added to all memory vectors
  #     whenever Request or Add is called
  #     When adding noise:
  #     memory vector = memory vector + noise * time since last update * noise vector
  #     Noise ranges from [0 ... ]
  #     where 0 is no noise
  #     and more is more noise
  
  def __init__(self,buffer,latency=0.05,threshold=-4.6,maximum_time=10.0,finst_size=4,finst_time=3.0, N=512, verbose=False, forgetting=1.0, noise=0.0):
    Memory.__init__(self,buffer)
    self._buffer=buffer
    self.N = N
    self.verbose = verbose
    self.env={'?': HRR(N=self.N)}
    self.placeholder = self.env['?']
    self.mem={}
    self.slots={')': numpy.random.permutation(self.N)}
    self.left=self.slots[')']
    self.error=False
    self.busy=False
    self.adaptors=[]
    self.latency=latency
    self.threshold=self.logodds_to_cosine(threshold)
    self.maximum_time=maximum_time
    self.partials=[]
    self.finst=Finst(self,size=finst_size,time=finst_time)
    self._request_count=0
    self.inhibited=[] # list of inhibited values
    self.forgetting=forgetting
    self.noise=noise
    self.lastUpdate = 0.0
    
  def clear(self):
    self.mem.clear()
    
  def add(self,chunk,record=None,**keys):
    # if error flag is true, set to false for production system
    if self.error: self.error=False
    # add noise to memory
    if (self.noise != 0):
        self.addNoise()
    # convert chunk to string (if it isn't already a string)
    chunk = self.chunk2str(chunk)
    # assign any unassigned values in chunk
    chunk = self.assignValues(chunk)
    # check if chunk has slots by checking for colons (which separate slots from values)
    if ':' in chunk:
        # call addWithSlots to add a chunk with slot:value pairs to memory
        self.addWithSlots(chunk)
    else:
        # call addJustValues to add a chunk with values and no slots to memory
        self.addJustValues(chunk)


  # function for adding noise over time to memory    
  def addNoise(self):
    # weight by time difference
    diff = self.now() - self.lastUpdate
    for value in self.mem.keys():
        noiseVector = HRR(N=self.N)
        self.mem[value] = self.mem[value] + (self.noise * diff * noiseVector)
    self.lastUpdate = self.now()
        

  def addWithSlots(self,chunk):
    # convert chunk to a list of (slot,value) pairs
    chunkList = self.chunk2list(chunk)
    # define random Gaussian vectors and random permutations for any undefined values and slots
    self.defineVectors(chunkList)
    # update the memory vectors with the information from the chunk
    for p in range(0,len(chunkList)):
        # create a copy of chunkList
        query = copy.deepcopy(chunkList)
        # replace p's value with ? in query, but leave slot as is
        query[p][1] = '?'
        print chunkList[p][1]
        print query
        # compute chunk vector
        chunkVector = self.getUOGwithSlots(query)
        # update memory
        self.updateMemory(chunkList[p][1],chunkVector)

  # add a chunk to memory
  # when the chunk is just a list of values
  # without slots
  def addJustValues(self,chunk):
    # convert chunk to a list of values
    chunkList = chunk.split()
    # define random Gaussian vectors for any undefined values
    self.defineVectors(chunkList)
    # update the memory vectors with the information from the chunk
    for p in range(0,len(chunkList)):
        # create a copy of chunkList
        query = copy.deepcopy(chunkList)
        # replace p with ? in query
        query[p] = '?'
        # compute chunk vector
        chunkVector = self.getUOG(query)
        # update memory
        self.updateMemory(chunkList[p],chunkVector)


  # function for constructing a vector that represents chunkList
  # where chunkList is a list of values without slots
  # and p is the location of ? in chunkList
  # returns chunk, an HRR representing all unconstrained open grams in chunkList
  # that include the ? at p.
  # When slots are not used, the permutation "left" is used to preserve order
  def getUOG(self, chunkList):
    numOfItems = len(chunkList)
    chunk = HRR(data=numpy.zeros(self.N))
    sum   = HRR(data=numpy.zeros(self.N))
    p     = numOfItems # initially, this will be set to index of ? when ? is found
    for i in range (0,numOfItems):
        # get the vector for the value i
        value = chunkList[i]
        # set p as the location of the placeholder ?
        if value == '?':
            p = i
        # if value starts with ! then negate the environment vector
        if value.startswith('!'):
            valVec = -1 * self.env[value[1:]]
        # otherwise use the environment vector as is
        else:
            valVec = self.env[value]
        # compute the chunk vector 
        if i == 0:
            sum = valVec
        elif (i > 0) and (i < p):
            leftOperand = chunk + sum
            leftOperand = leftOperand.permute(self.left)
            chunk       = chunk + leftOperand.convolve(valVec)
            sum         = sum + valVec
        elif i == p:  # force all skip grams to include item p
            leftOperand = chunk + sum
            leftOperand = leftOperand.permute(self.left)
            chunk       = leftOperand.convolve(valVec)
            sum         = valVec
        else: # i > p, i > 0
            leftOperand = chunk + sum
            leftOperand = leftOperand.permute(self.left)
            chunk       = chunk + leftOperand.convolve(valVec)
    return chunk


  # function for constructing a vector that represents chunkList
  # where chunkList is a list of values WITH slots as permutations
  # returns chunk, an HRR representing all unconstrained open grams in chunkList
  # that include the ?
  def getUOGwithSlots(self, chunkList):
    numOfItems = len(chunkList)
    chunk = HRR(data=numpy.zeros(self.N))
    sum   = HRR(data=numpy.zeros(self.N))
    #sumStr = ''
    #chunkStr = ''
    p     = numOfItems # initially, this will be set to index of ? when ? is found
    for i in range (0,numOfItems):
        # get the vector for the slot value pair at i
        slotvalue = chunkList[i]
        slot  = slotvalue[0]
        value = slotvalue[1]
        # set p as the location of the placeholder ?
        if value == '?':
            p = i
        # if value starts with ! then negate the environment vector
        if value.startswith('!'):
            valVec = -1 * self.env[value[1:]]
        # otherwise use the environment vector as is
        else:
            valVec = self.env[value]
        # permute the environment vector by the slot
        valVec = valVec.permute(self.slots[slot])
        #slotvalueStr = slot+':'+value
        # compute the chunk vector 
        if i == 0:
            sum = valVec
            #sumStr = slotvalueStr
        elif (i > 0) and (i < p):
            leftOperand = chunk + sum
            chunk       = chunk + leftOperand.convolve(valVec)
            #chunkStr    = chunkStr + ' + ' + slotvalueStr + ' * (' +  chunkStr + ' + ' + sumStr + ')'
            sum         = sum + valVec
            #sumStr      = sumStr + ' + ' + slotvalueStr
        elif i == p:  # force all skip grams to include item p
            leftOperand = chunk + sum
            chunk       = leftOperand.convolve(valVec)
            #chunkStr    = slotvalueStr + ' * (' +  chunkStr + ' + ' + sumStr + ')'
            sum         = valVec
            #sumStr      = slotvalueStr
        else: # i > p, i > 0
            leftOperand = chunk + sum
            chunk       = chunk + leftOperand.convolve(valVec)
            #chunkStr    = chunkStr + ' + ' + slotvalueStr + ' * (' +  chunkStr + ' + ' + sumStr + ')'
    return chunk #, chunkStr


  # for updating a memory vector for value with chunk
  def updateMemory(self,value,chunking):
    if value.startswith('!'):
        if value[1:] not in self.mem:
            self.mem[value[1:]] = -1*chunking
        else:
            self.mem[value[1:]] = self.forgetting * self.mem[value[1:]] - chunking
    else:
        if value not in self.mem:
            self.mem[value] = chunking
        else:
            self.mem[value] = self.forgetting * self.mem[value] + chunking


  # default request function, call this
  def request(self,chunk,require_new=False):
     self.busy=True
     if self.error: self.error=False
     self._request_count+=1

     
     # add noise to memory
     if (self.noise != 0):
        self.addNoise()

     # clear list of inhibited values from previous queries
     self.inhibited = []
     # convert chunk to string (if it isn't already a string)
     chunk = self.chunk2str(chunk)
     # assign any unassigned values in chunk string and load inhibited values into self.inhibited
     chunk = self.assignValues(chunk)
     if '?' in chunk:
        self.requestValue(chunk,require_new)
     else:
        self.resonance(chunk)


  def requestValue(self,chunk,require_new=False):
     # check if chunk has slots by checking for colons (which separate slots from values)
     if ':' in chunk:
        queryVec = self.queryWithSlots(chunk)
     else:
        queryVec = self.queryJustValues(chunk)
     
     highestCosine = self.threshold
     bestMatch = 'none'
     if self.verbose:
        print 'Query is: ' + chunk
        print 'inhibited values: ' + str(self.inhibited)
        print 'Finst contains: ' + str(self.finst.obj)
     # find the best match to the query vector in memory
     for mem,memVec in self.mem.items():
        # skip inhibited values
        if mem not in self.inhibited:
            # skip previously reported values if require_new is true
            if (not require_new) or (not self.finst.contains(mem)):
                thisCosine = memVec.compare(queryVec)
                if self.verbose:
                    print mem, thisCosine
                if thisCosine > highestCosine:
                    highestCosine = thisCosine 
                    bestMatch = mem

     if bestMatch == 'none':
        if self.verbose:
            print 'No matches found above threshold of cosine =', self.threshold
        self.fail(self._request_count)
     else:
         # replace the placeholder '?' with the retrieved memory 'bestMatch'
         chunk = chunk.replace('?',bestMatch)
         if self.verbose:
            print 'Best match is ' + bestMatch
            print 'with a cosine of ' + str(highestCosine)
            print 'output chunk = ' + chunk
         chunkObj = Chunk(chunk)
         chunkObj.activation = highestCosine
         self.finst.add(bestMatch)
         self.recall(chunkObj,matches=[],request_number=self._request_count)
  
  # performs multiple queries to determine the "coherence" of the chunk
  def resonance(self,chunk):
     if '?' in chunk:
        print 'chunk is ' + chunk
        raise Exception("Use the resonance function when the chunk has no '?'. If there is a '?' use request instead")
          
     coherence = self.get_activation(chunk)
     if self.verbose:
        print 'The coherence is ' + str(coherence)
     if coherence <= self.threshold:
        self.fail(self._request_count)
     else:
         chunkObj = Chunk(chunk)
         chunkObj.activation = coherence
         self.recall(chunkObj,matches=[],request_number=self._request_count)     

  # compute the coherence / activation of a chunk
  # called by resonance
  # called by request when no ? values are present
  # if logodds=True, the convert from mean cosine to logodds and return logodds
  def get_activation(self,chunk,logodds=False):
     # if this function has been called directly, we need to convert
     if not self.busy:
        # convert chunk to string (if it isn't already a string)
        chunk = self.chunk2str(chunk)
        # assign any unassigned values in chunk string and load inhibited values into self.inhibited
        chunk = self.assignValues(chunk)
        # add noise to memory
        if (self.noise != 0):
            self.addNoise()

     # keep track of the number of occurrences of a particular value in case of repeats
     occurrences = {}
     # keep a running sum of the cosines and a count of the values in the chunk
     sumOfCosines = 0;
     numOfValues  = 0; 
     # perform a query for each value in chunk
     for slotvalue in chunk.split():
        # create a query by removing the value and replacing it with '?'
        query = chunk.split() # turn chunk into list
        query.pop(numOfValues) # remove this list item
        # check if chunk has slots by checking for colons (which separate slots from values)
        if ':' in slotvalue:
            slot,value = slotvalue.split(':')
            query.insert(numOfValues, slot+':?') # replace value with ?
            query = ' '.join(query) # convert query to a string
            queryVec = self.queryWithSlots(query)
        else:
            value = slotvalue
            query.insert(numOfValues, '?') # replace value with ?
            query = ' '.join(query) # convert query to a string
            queryVec = self.queryJustValues(query)
        numOfValues = numOfValues + 1;

        # find the match between the query vector and the value's memory vector
        self.defineVectors([value])
        match = self.mem[value].compare(queryVec)
        sumOfCosines = sumOfCosines + match
     coherence = sumOfCosines / numOfValues
     if logodds:
        return self.cosine_to_logodds(coherence)
     else:
        return coherence

  # create a query vector for a chunk consisting of slot:value pairs
  # the query vector consists of the open n-grams of the slot:value pairs
  # only open n-grams that contain ? are included
  # the query vector must have one and only one query item "?"
  def queryWithSlots(self,chunk):
     # convert chunk to a list of (slot,value) pairs
     chunkList = self.chunk2list(chunk)
     # define random Gaussian vectors and random permutations for any undefined values and slots
     self.defineVectors(chunkList)
     # construct the query vector
     queryVec = self.getUOGwithSlots(chunkList)
     return queryVec
    
  # create a query vector for a chunk consisting of slot:value pairs
  # the query vector consists of the open n-grams of the values
  # only n-grams that contain ? are included
  # the query vector must have one and only one query item "?"
  def queryJustValues(self,chunk):
     # convert chunk to a list of values
     chunkList = chunk.split()
     # define random Gaussian vectors for any undefined values
     self.defineVectors(chunkList)
     # get all combinations ranging from pairs of slot-value pairs to sets
     queryVec = self.getUOG(chunkList)
     return queryVec

  # chunk2str converts a chunk into a string
  # or if it is already a string, chunk2str just returns the string unmodified
  def chunk2str(self,chunk):
    # if the chunk is a Buffer object, extract the Chunk object from inside it, then turn the Chunk into a string
    if isinstance(chunk,Buffer):
        chunk = Chunk(chunk.chunk)
    # if the chunk is a Chunk object, turn the Chunk into a string
    if isinstance(chunk,Chunk):
        chunk = str(chunk)
    return chunk

  # chunk2list converts a chunk into a list of (slot,value) pairs
  def chunk2list(self,chunk):
    if ':' in chunk:
        return [item.split(':') for item in chunk.split()]
    else:
        raise Exception("Wrong chunk format!")
        return None
  
  # assignValues checks for unassigned values, i.e., '?stuff'
  # returns chunk as a string
  def assignValues(self,chunk):
    # convert chunk to str (if it isn't already)
    chunk = self.chunk2str(chunk)
    # replace instances of ?stuff with corresponding stuff
    bound=None
    if hasattr(self,'sch'):
        bound=getattr(self.sch,'bound',None)
    # split the chunkStr where there are spaces to get the list of attributes
    attributes = chunk.split()
    # find ?values that need to be substituted
    chunkList = []
    for attribute in attributes:
        # this function needs to handle both chunks that are lists of slot:value pairs
        # and chunks that are ordered lists of values
        if ':' in attribute:
            slot,value = attribute.split(':')
            slot = slot + ':'
        else:
            value = attribute
            slot  = '' 
        # sometimes we want to specify things not to select
        # for example, condiment:?unknown!mustard
        # means find a condiment that isn't mustard
        if value.startswith('?') and value is not '?':
            first = True
            for subvalue in value.split('!'):
                # we know the first value starts with ?, so let's substitute
                if first:
                    first = False;
                    #check to see if it's not just a ? by itself
                    if subvalue is '?':
                        value = '?'
                    else:
                        try:
                            # take "?value" without the "?"
                            key = subvalue[1:]
                            # look it up in the "bound dictionary" and substitute
                            value = bound[key]
                        # if "value" in "?value" is undefined, replace with "?"
                        except:
                            value = '?'
                # the following values all start with ! meaning things we don't want to retrieve
                else:
                    if subvalue.startswith('?'):
                        # but some of them may start with ? indicating we need to substitute
                        try:
                            # take "?value" without the "?"
                            key = subvalue[1:]
                            # look it up in the "bound dictionary" and add to inhibited values list
                            subvalue = bound[key]
                        # if "value" in "?value" is undefined, raise exception
                        except:
                            print chunk
                            print 'Error with subvalue: ' + subvalue + ' in chunk: ' + chunk
                            raise Exception('Values beginning with ! are understood in this context as indicating values to be inhibited. The specified !value is undefined')
                    # add subvalue to inhibition list
                    self.inhibited.append(subvalue)

        # add the value to the chunkList
        chunkList.append(slot+value)
    # convert chunkList into a string delimited by spaces
    return ' '.join(chunkList)
  
  
  #get environment vector for a given value
  def get(self,value):
    if value not in self.env:
        self.env[value] = HRR(N=self.N)
        self.mem[value] = HRR(data=numpy.zeros(self.N))
    return self.env[value].copy()
  
  
  #set environment vector for a given value to a specified vector
  def set(self,value,vector):
    try: # assume vector is an HRR object
        newVec = vector.copy()
        newVec.normalize()
        self.env[value] = newVec
    except: # assume vector is a list of numbers
        vector = [float(i) for i in vector]
        self.env[value] = HRR(data=vector)
        self.env[value].normalize()
    # check to see if it's in memory already, if not, define its memory as a vector of zeros
    if value not in self.mem:
        self.mem[value] = HRR(data=numpy.zeros(self.N))


  # generate Gaussian vectors and random permutations for values & slots without
  # chunkList is a list of attributes, each attribute is a string
  def defineVectors(self,chunkList):
    for attribute in chunkList:
        # check to see if there is a slot, or if it's just a value without a slot
        if isinstance(attribute,list):
            slot,value = attribute
            # if it's a new slot, create a new random permutation
            if slot not in self.slots.keys():
                self.slots[slot] = numpy.random.permutation(self.N)
        else:
            value = attribute  
        # if it starts with ! (i.e., not) just ignore that for now
        if value.startswith('!'):
            value = value[1:]
        # if it's a new value, create a new random vector
        if value not in self.env:
            self.env[value] = HRR(N=self.N)
            self.mem[value] = HRR(data=numpy.zeros(self.N))#self.env[value]
  
       
  def fail(self,request_number):
     if self.threshold is None: 
         time=self.maximum_time
     else:
         logodds = self.cosine_to_logodds(self.threshold)
         time=self.latency*math.exp(-logodds)
         if time>self.maximum_time: time=self.maximum_time 
     yield time
     if request_number!=self._request_count: return
     
     self.error=True
     self._buffer.clear()
     self.busy=False
  
  def recall(self,chunk,matches,request_number):
     logodds = self.cosine_to_logodds(chunk.activation)
     time=self.latency*math.exp(-logodds)
     if time>self.maximum_time: time=self.maximum_time
     yield time
     if request_number!=self._request_count: return
     self._buffer.set(chunk)
     for a in self.adaptors: a.recalled(chunk)
     self.busy=False
     
# Converts vector cosine (which approximates root probability)
# to a log odds ratio (which is what ACT-R activation estimates) 
  def cosine_to_logodds(self,cosine):
        if cosine > 0.999:
            cosine = 0.999
        return math.log(cosine**2 / (1 - cosine**2))

# Converts log odds ratio or ACT-R activation
# to a root probability (which the cosine approximates)
  def logodds_to_cosine(self,logodds):
        return math.sqrt(numpy.exp(logodds) / (numpy.exp(logodds) + 1))

class Finst:
  def __init__(self,parent,size=4,time=3.0):
    self.parent=parent
    self.size=size
    self.time=time
    self.obj=[]
  def contains(self,o):
    return o in self.obj
  def add(self,o):
    if self.size==0: return
    self.obj.append(o)
    if len(self.obj)>self.size:
      self.remove(self.obj[0])
    self.parent.sch.add(self.remove,args=[o],delay=self.time)
  def remove(self,o):
    if o in self.obj: self.obj.remove(o)