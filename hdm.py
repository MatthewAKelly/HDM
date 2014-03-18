from __future__ import generators
import ccm
import math
import numpy

__all__=['HDM']

from ccm.lib.actr.buffer import Chunk,Buffer
# add for hdm
from ccm.lib.actr.dm import Memory
from ccm.pattern import Pattern
from ccm.lib.hrr import HRR

class HDM(Memory):
  # buffer is the buffer that the retrieved chunk is placed in
  # N is the vector dimensionality
  #     recommended dimensionality in the range of 512 to 2048, defaults to 1024
  #     a smaller dimensionality than 512 can be used to introduce additional noise
  # threshold is the lowest cosine similarity allowed for a response
  #     if no memory vector has a similarity to the query greater than threshold, the retrieval fails
  # maximum time is the most time the memory system is allowed to take
  # latency is used to calculate reaction time
  #     reaction time = latency * e^(-cosine)
  #     Note that using this equation, given a cosine of 0, the reaction time = latency
  #     Bigger latencies result in longer reaction times
  def __init__(self,buffer,latency=0.05,threshold=0,maximum_time=10.0,finst_size=4,finst_time=3.0, N=1024):
    Memory.__init__(self,buffer)
    self._buffer=buffer
    self.hdm=[]
    self.N = N
    self.environment={'?': HRR(N=self.N)}
    self.placeholder = self.environment['?']
    self.cLambda = 7
    self.memory={}
    self.memStr={}
    self.slots={')': numpy.random.permutation(self.N)}
    self.left=self.slots[')']
    self.error=False
    self.busy=False
    self.adaptors=[]
    self.latency=latency
    self.threshold=threshold
    self.maximum_time=maximum_time
    self.partials=[]
    self.finst=Finst(self,size=finst_size,time=finst_time)
    self.record_all_chunks=False
    self._request_count=0
    
  def clear(self):
    del self.hdm[:]
    
  def add(self,chunk,record=None,**keys):
    # if error flag is true, set to false for production system
    if self.error: self.error=False
    
    # convert chunk to string (if it isn't already a string)
    chunk = self.chunk2str(chunk)
    # assign any unassigned values in chunk
    self.assignValues(chunk)
    # check if chunk has slots by checking for colons (which separate slots from values)
    if ':' in chunk:
        # call addWithSlots to add a chunk with slot:value pairs to memory
        self.addWithSlots(chunk)
    else:
        # call addJustValues to add a chunk with values and no slots to memory
        self.addJustValues(chunk)
        

  def addWithSlots(self,chunk):
    # convert chunk to a list of (slot,value) pairs
    chunkList = self.chunk2list(chunk)
    # define random Gaussian vectors and random permutations for any undefined values and slots
    self.defineVectors(chunkList)
    # get all combinations ranging from individual slot-value pairs to sets of self.cLambda size
    ngrams = self.getOpenNGrams(chunkList,range(1,self.cLambda+1))
    
    # update the memory vectors with the information from the chunk
    for gram in ngrams:
        for p in xrange(len(gram)):
            for i in xrange(len(gram)):
                (slot,value) = gram[i]
                slotPerm = self.slots[slot]
                if i == p:
                    # replace with placeholder
                    valVec = self.environment['?']
                    slotvalStr = slot + '(?)'
                else:
                    if value.startswith('!'):
                        valVec = -1 * self.environment[value[1:]]
                    else:
                        valVec = self.environment[value]     
                    slotvalStr = slot + '('+value+')'
                # permute the value's vector by the slot's permutation & store that
                slotvalVec = valVec.permute(slotPerm)
                
                if i == 0:
                    chunking = slotvalVec
                    chunkStr = slotvalStr
                else:
                    chunking = chunking * slotvalVec
                    chunkStr = chunkStr+'*'+slotvalStr   
            # update memory
            (slot,value) = gram[p]
            if value.startswith('!'):
                self.memory[value] = self.memory[value[1:]] - chunking
            else: 
                self.memory[value] = self.memory[value] + chunking
                
            try:
                self.memStr[value] = self.memStr[value] +' + '+ chunkStr
            except:
                self.memStr[value] = chunkStr


      
      
  def addJustValues(self,chunk):
    # convert chunk to a list of values
    chunkList = chunk.split()
    # define random Gaussian vectors for any undefined values
    self.defineVectors(chunkList)
    # get all combinations ranging from pairs of values to sets of self.cLambda size
    ngrams = self.getOpenNGrams(chunkList,range(2,self.cLambda+1))
    
    # update the memory vectors with the information from the chunk
    for gram in ngrams:
        for p in xrange(len(gram)):
            for i in xrange(len(gram)):
                value = gram[i]
                if i == p:
                    # replace with placeholder
                    valVec = self.environment['?']
                    valStr = '?'
                else:
                    if value.startswith('!'):
                        valVec = -1 * self.environment[value[1:]]
                    else:
                        valVec = self.environment[value]     
                    valStr = value
                
                if i == 0:
                    chunking = valVec
                    chunkStr = valStr
                else:
                    # permute the left operand of the convolution to make convolution asymmetric
                    # for this purpose we use a special permutation that we're calling "left"
                    chunking = chunking.permute(self.left) * valVec
                    chunkStr = chunkStr+'*'+valStr   
            # update memory
            value = gram[p]
            if value.startswith('!'):
                self.memory[value] = self.memory[value[1:]] - chunking
            else: 
                self.memory[value] = self.memory[value] + chunking
                
            try:
                self.memStr[value] = self.memStr[value] +' + '+ chunkStr
            except:
                self.memStr[value] = chunkStr


  def request(self,chunk,partial=None,require_new=False):
     if partial is None and len(self.partials)>0: partial=self.partials[0]
     self.busy=True
     if self.error: self.error=False
     self._request_count+=1

     
     # convert chunk to string (if it isn't already a string)
     chunk = self.chunk2str(chunk)
     # assign any unassigned values in chunk string
     chunk = self.assignValues(chunk)
     
     # check if chunk has slots by checking for colons (which separate slots from values)
     if ':' in chunk:
        queryVec, queryStr = self.queryWithSlots(chunk)
     else:
        queryVec, queryStr = self.queryJustValues(chunk)
     
     print 'The query is ' + queryStr
     highestCosine = self.threshold
     bestMatch = 'none'
     # find the best match to the query vector in memory
     for mem,memVec in self.memory.items():
        thisCosine = memVec.compare(queryVec)
        print mem, thisCosine
        if thisCosine > highestCosine:
            highestCosine = thisCosine 
            bestMatch = mem
     print bestMatch

     if bestMatch == 'none':
        self.fail(self._request_count)
     else:
         print 'Best match is ' + bestMatch + ' = ' + self.memStr[bestMatch]
         # replace the placeholder '?' with the retrieved memory 'bestMatch'
         chunk = chunk.replace('?',bestMatch)
         print 'output chunk = ' + chunk
         chunkObj = Chunk(chunk)
         chunkObj.activation = highestCosine
         self.recall(chunkObj,matches=[],request_number=self._request_count)
        
        
        
  def queryWithSlots(self,chunk):
     # convert chunk to a list of (slot,value) pairs
     chunkList = self.chunk2list(chunk)
     # define random Gaussian vectors and random permutations for any undefined values and slots
     self.defineVectors(chunkList)
     # get all combinations ranging from individual slot-value pairs to sets of self.cLambda size
     ngrams = self.getOpenNGrams(chunkList,range(1,self.cLambda+1))

     # filter out ngrams that don't contain a ?
     queryGrams = []
     for gram in ngrams:
        there_is_one_placeholder  = False
        for [slot,value] in gram:
            if value is '?':
                if there_is_one_placeholder:
                    there_is_one_placeholder = False
                    raise Exception('HDM requests must have no more than one ?')
                else:
                    there_is_one_placeholder = True
                
        if there_is_one_placeholder:
            queryGrams.append(gram)
     if not queryGrams:
        raise Exception('HDM requests must have at least one ?')
     else:
         # construct the query vector as a sum of queryGrams vectors
         # where each queryGram vector is constructed by binding slotvalue vectors
         # where each slotvalue vector is a slot permutation of a value vector
         for j,gram in enumerate(queryGrams):
            for i, slotvalue in enumerate(gram):
                [slot,value] = slotvalue
                slotPerm = self.slots[slot]
                if value.startswith('!'):
                    valVec = -1 * self.environment[value[1:]]
                else:
                    valVec = self.environment[value]     
                # permute the value's vector by the slot's permutation
                slotvalVec = valVec.permute(slotPerm)
                if i == 0:
                    # base case
                    chunkStr = slot+'('+value+')'
                    chunking = slotvalVec
                else:
                    chunkStr = chunkStr+'*'+slot+'('+value+')'
                    chunking = chunking * slotvalVec
            if j == 0:
                queryStr = chunkStr
                queryVec = chunking
            else:
                queryStr = queryStr+' + '+chunkStr
                queryVec = queryVec + chunking
     return queryVec, queryStr 
    

  def queryJustValues(self,chunk):
     # convert chunk to a list of values
     chunkList = chunk.split()
     # define random Gaussian vectors for any undefined values
     self.defineVectors(chunkList)
     # get all combinations ranging from pairs of slot-value pairs to sets of self.cLambda size
     ngrams = self.getOpenNGrams(chunkList,range(2,self.cLambda+1))

     # filter out ngrams that don't contain a ?
     queryGrams = []
     for gram in ngrams:
        there_is_one_placeholder  = False
        for value in gram:
            if value is '?':
                if there_is_one_placeholder:
                    there_is_one_placeholder = False
                    raise Exception('HDM requests must have no more than one ?')
                else:
                    there_is_one_placeholder = True
                
        if there_is_one_placeholder:
            queryGrams.append(gram)
            
     if not queryGrams:
        raise Exception('HDM requests must have at least one ?')
     else:
         # construct the query vector as a sum of queryGrams vectors
         # where each queryGram vector is constructed by binding value vectors
         # we make binding non-commutative by permuting the left operand using the "left" permutation
         for j,gram in enumerate(queryGrams):
            for i, value in enumerate(gram):
                if value.startswith('!'):
                    valVec = -1 * self.environment[value[1:]]
                else:
                    valVec = self.environment[value]     
                if i == 0:
                    # base case
                    chunkStr = value
                    chunking = valVec
                else:
                    chunkStr = chunkStr+'*'+value
                    chunking = chunking.permute(self.left) * valVec
            if j == 0:
                queryStr = chunkStr
                queryVec = chunking
            else:
                queryStr = queryStr+' + '+chunkStr
                queryVec = queryVec + chunking
     return queryVec, queryStr 
                


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
        if value.startswith('?') and value is not '?':
            try:
                # take "?value" without the "?"
                key = value[1:]
                # look it up in the "bound dictionary" and substitute
                value = bound[key]
            # if "value" in "?value" is undefined, replace with "?"
            except:
                value = '?'
        # add the value to the chunkList
        chunkList.append(slot+value)
    # convert chunkList into a string delimited by spaces
    return ' '.join(chunkList)
  
  # generate Gaussian vectors and random permutations for values & slots without
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
        if value not in self.environment.keys():
            self.environment[value] = HRR(N=self.N)
            self.memory[value] = HRR(data=numpy.zeros(self.N))#self.environment[value]

  

  def getOpenNGrams(self, seg, scale, spaces=None):
    '''
    Returns a list of the open n-grams of the string "seg", with sizes specified
    by "scale", which should be a list of positive integers in ascending order.
    "Spaces" indicates whether a space character should be used to mark gaps in
    non-contiguous n-grams.
    '''
    ngrams = []
    
    for size in scale:
        if size > len(seg): break
    
        for i in xrange(len(seg)):
            if i+size > len(seg): break
            ngrams.append(seg[i:i+size])
            if i+size == len(seg): continue
            for b in xrange(1, size):
                for e in xrange(1, len(seg)-i-size+1):
                    if spaces is None:
                        ngrams.append(seg[i:i+b] + seg[i+b+e:i+e+size])
                    else:
                        ngrams.append(seg[i:i+b] + [spaces] + seg[i+b+e:i+e+size])
    return ngrams
     
  def fail(self,request_number):
     if self.threshold is None: 
         time=self.maximum_time
     else:
         time=self.latency*math.exp(-self.threshold)
         if time>self.maximum_time: time=self.maximum_time 
     yield time
     if request_number!=self._request_count: return
     
     self.error=True
     self._buffer.clear()
     self.busy=False
  
  def recall(self,chunk,matches,request_number):
     self.finst.add(chunk)
     time=self.latency*math.exp(-chunk.activation)
     if time>self.maximum_time: time=self.maximum_time
     yield time
     if request_number!=self._request_count: return
     self._buffer.set(chunk)
     for a in self.adaptors: a.recalled(chunk)
     self.busy=False
     
  

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