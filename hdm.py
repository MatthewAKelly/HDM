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
#   max_gram_size is the largest n-gram size that the model uses
#       Defaults to a generous 7-grams
#       Chunks stored in memory are stored as associations 
#       between up to max_gram_size slot-values   
#   verbose defaults to False
#       set to True if you want to see what HDM is doing in detail
# HDM also has some parameters that DM has and that are still important:   
#   buffer is the buffer used to output chunks retrieved from HDM
#   latency is F in Fe^-a, where a is the activation calculated as vector cosine
#   threshold is the minimum cosine, less than threshold and a retrieval failure occurs
#   threshold defaults to 0.1 as a cosine of around zero means the data in HDM is totally irrelevant
#
# HDM has three important functions to call:
# add(chunk): adds a chunk to memory
# request(chunk): 
#       Given a chunk with exactly one unknown value '?', 
#       request finds the best value to fill '?'
#       which it returns
#       Reaction time is a function of cosine (similarity of chunk to memory)
# resonance(chunk):
#       Given a chunk with no unknown values,
#       resonance will return the chunk if it is familiar 
#       or fail to return the chunk if it is unfamiliar
#       i.e., has a cosine less than threshold
#       Reaction time is a function of cosine (similarity of chunk to memory)

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
  # verbose defaults to FALSE. 
  #     If TRUE, verbose turns on print statements giving details about what HDM is doing.
  def __init__(self,buffer,latency=0.05,threshold=0.1,maximum_time=10.0,finst_size=4,finst_time=3.0, N=512, verbose=False, max_gram_size=7):
    Memory.__init__(self,buffer)
    self._buffer=buffer
    self.N = N
    self.verbose = verbose
    self.environment={'?': HRR(N=self.N)}
    self.placeholder = self.environment['?']
    self.cLambda = max_gram_size
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
    self.memory.clear()
    
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


  def request(self,chunk):
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
     
     if self.verbose:
        print 'The query is ' + queryStr
     highestCosine = self.threshold
     bestMatch = 'none'
     # find the best match to the query vector in memory
     for mem,memVec in self.memory.items():
        thisCosine = memVec.compare(queryVec)
        if self.verbose:
            print mem, thisCosine
        if thisCosine > highestCosine:
            highestCosine = thisCosine 
            bestMatch = mem
     if self.verbose:
        print bestMatch

     if bestMatch == 'none':
        self.fail(self._request_count)
     else:
         # replace the placeholder '?' with the retrieved memory 'bestMatch'
         chunk = chunk.replace('?',bestMatch)
         if self.verbose:
            print 'Best match is ' + bestMatch + ' = ' + self.memStr[bestMatch]
            print 'output chunk = ' + chunk
         chunkObj = Chunk(chunk)
         chunkObj.activation = highestCosine
         self.recall(chunkObj,matches=[],request_number=self._request_count)
  
  # performs multiple queries to determine the "coherence" of the chunk
  def resonance(self,chunk):
     self.busy=True
     if self.error: self.error=False
     self._request_count+=1


     # convert chunk to string (if it isn't already a string)
     chunk = self.chunk2str(chunk)
     # assign any unassigned values in chunk string
     chunk = self.assignValues(chunk)

     if '?' in chunk:
        raise Exception("Use the resonanuce function when the chunk has no '?'. If there is a '?' use request instead")
          
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
            queryVec, queryStr = self.queryWithSlots(query)
        else:
            value = slotvalue
            query.insert(numOfValues, '?') # replace value with ?
            query = ' '.join(query) # convert query to a string
            queryVec, queryStr = self.queryJustValues(query)
        numOfValues = numOfValues + 1;

        # find the match between the query vector and the value's memory vector
        match = self.memory[value].compare(queryVec)
        sumOfCosines = sumOfCosines + match
        if self.verbose:
            print 'The query is ' + queryStr
            print 'Match is ' + str(match) + ' for ' + value + ' = ' + self.memStr[value]
     coherence = sumOfCosines / numOfValues
     if self.verbose:
        print 'The coherence is ' + str(coherence)
     if coherence <= self.threshold:
        self.fail(self._request_count)
     else:
         chunkObj = Chunk(chunk)
         chunkObj.activation = coherence
         self.recall(chunkObj,matches=[],request_number=self._request_count)     


  # create a query vector for a chunk consisting of slot:value pairs
  # the query vector consists of the open n-grams of the slot:value pairs
  # only open n-grams that contain ? are included
  # the query vector must have one and only one query item "?"
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
        raise Exception('HDM requests must have at least one value that is ?')
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
    
  # create a query vector for a chunk consisting of slot:value pairs
  # the query vector consists of the open n-grams of the values
  # only n-grams that contain ? are included
  # the query vector must have one and only one query item "?"
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