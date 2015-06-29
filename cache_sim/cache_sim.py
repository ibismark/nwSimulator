# -*- coding: utf-8 -*-

"""
2015/02/03  last update
Python3.3 Simpy3

トポロジー(simple ver)
Terminal ---  router ---  router
                 |           |
	    cache server    cms

# キャッシュ置換アルゴリズムをコマンドライン引数で受け取るようにはなってない
# 都度呼び出しをコメントアウトして使用(デフォルトではMCDとLRUを使用)
	ex) lru fifo bias unif,   always fix lcd mcd

# 時間単位をμで刻むため、1時間のシミュレートで15分程度

# コンテンツの人気度分布はZipfの法則に従う
"""


import simpy
import sys
import math
import random

import zipf

# Link speed, MTU, Delay, Window size
ls = dict( c0 = [100.0*10**6/8.0, 1400, 5.0*10**3, 0.6, 10],
	s0=[2400.0*10**6/8.0, 9000, 50.0*10**3, 0.6, 10]
	)


cache = list()		      #cache data in
maxCacheSlots = 10000 #1GBytes=10000 100MBytes=1000 10MBytes=100
maxCacheNumber = 15
simulationTime = 3600 *10**6  #hour[μs]
devide = 100                  #chunk/file
fileSize = 10**7              #10MBytes
chunkSize = 10**5             #100KBytes
contentNum = 300              #anumber of content
t = dict()
t2 = dict()

recque = dict()
waitque = dict()
endque = list()
ifque = dict()
fcount = dict()



def initCache(env):
	for i in range(maxCacheNumber):
		na = i+1
		mm = 'c' + str(na)
		recque[na] = list()
		waitque[na] = list()
		ifque[mm] = simpy.Resource(env, capacity=1)
	for j in range(maxCacheSlots):
		cache.append([None, None, 0])

	recque[na+1] = list()
	waitque[na+1] = list()
	mm='c' + str(na+1)
	ifque[mm] = simpy.Resource(env, capacity=1)

	return


def makeEvent(tranCount):
	tev, f, t, a = [], '', '', 0	
	e = zipf.zipf(contentNum, tranCount+1)

	for t in range(tranCount):
		r = random.random()
		t = 't%04d' %t
		a = math.ceil((r*3600)*10**6)
		r = random.random()
		f = 'f' + str(e.pop(0))
		tev.append([t, f, a])

	return tev


class Tran(object):
	def __init__(self, env, tname, fname, arriveTime):
		self.env = env
		self.tname = tname
		self.fname = fname
		self.arriveTime = arriveTime
		self.hopCount = 1
		self.action = env.process(self.run())

	
	def run(self):
		yield self.env.timeout(self.arriveTime)

		fcount[self.tname] = [0, 0]
		print("start:  ", self.tname, self.arriveTime)
		for i in range(devide):
			recque[1].append([self.fname, self.tname, 0, self.hopCount, self.arriveTime, i])
		return


class cmsServ(object):
	def __init__(self, env, num, sc):
		self.env = env
		self.l = num
		self.sc = sc
		self.locks0=0
		self.lockwa=0
		self.wait = ls['s0'][1]*ls['s0'][4] / ls['s0'][0]*10**6 / ls['s0'][4]
		self.delay = ls['s0'][2]
		self.count = int(math.ceil(chunkSize/ls['s0'][1]/ls['s0'][4]))
		self.action = self.env.process(self.retr())


	def sendQue(self):
		self.locks0=1
		self.fname, self.tname, self.dest, self.hopCount, self.arriveTime, self.block = waitque[self.l][0]
		if self.dest==-1:
			with ifque[self.sc].request() as req:
				yield req
				for i in range(self.count):
					if i%ls['s0'][4] == 0:
						yield self.env.timeout(self.delay)
					yield self.env.timeout(self.wait)
			
				recque[self.l-1].append(waitque[self.l].pop(0))
				self.locks0 = 0
		else:
			recque[self.l-1].append(waitque[self.l].pop(0))
			
		return


	def always(self):
		for i in range(maxCacheNumber):
			if self.findCache(maxCacheNumber-i) < 0:
				waitque[self.l].append([self.fname, self.tname, maxCacheNumber-i, self.hopCount, self.arriveTime, self.block])
		return


	def mcd(self):
		waitque[self.l].append([self.fname, self.tname, self.l-1, self.hopCount, self.arriveTime, self.block])
		return


	def lcd(self):
		waitque[self.l].append([self.fname, self.tname, self.l-1, self.hopCount, self.arriveTime, self.block])
		return


	def fCache(self, hop):
		for i in range(maxCacheSlots):
			if t2[hop].cache[i][0] == self.fname and t2[hop].cache[i][1] == self.block:
				return i
		return -1


	def retr(self):
		while True:
			yield self.env.timeout(1000)
			if recque[self.l] != []:
				self.fname, self.tname, self.dest, self.hopCount, self.arriveTime, self.block = recque[self.l][0]
				if self.dest:
					return
				waitque[self.l].append([self.fname, self.tname, -1, self.hopCount, self.arriveTime, self.block])
				a = recque[self.l].pop(0)

				if self.fCache(self.l-1) < 0:
					#self.always()
					self.mcd()
					#self.lcd()
					#self.fix()

			if waitque[self.l] != [] and self.locks0 == 0:
				yield self.env.process(self.sendQue())
			else:
				self.locks0=0




class cacheServ(object):
	def __init__(self, env, cache, num, sc):
		self.env = env
		self.cache = cache[:]
		self.l = num
		self.sc = sc
		self.fque = list()
		self.locks0 = 0
		self.chk = 0

		if self.l == 1:
			self.wait = ls['c0'][1]*ls['c0'][4] / ls['c0'][0]*10**6 / ls['c0'][4]
			self.delay = ls['c0'][2]
			self.count = int(math.ceil(chunkSize/ls['c0'][1]/ls['c0'][4]))
			self.h = 'c0'
			self.c = 0
		else:
			self.wait = ls['s0'][1]*ls['s0'][4] / ls['s0'][0]*10**6 / ls['s0'][4]
			self.delay = ls['s0'][2]
			self.count = int(math.ceil(chunkSize/ls['s0'][1]/ls['s0'][4]))
			self.h = 's0'

		self.action = self.env.process(self.retr())


	def fifo(self):
		if len(self.fque) == maxCacheSlots:
			f, b = self.fque.pop(0)
			for i in range(maxCacheSlots):
				if self.cache[i][0] == f and self.cache[i][1] == b:
					self.cache[i] = [self.fname, self.block, 0]
					self.fque.append([self.fname, self.block])
					break
		return


	def lru(self):
		for i in range(len(self.fque)):
			if self.fque[i][0] == self.fname and self.fque[i][1] == self.block:
				f = self.fque[i][0]
				b = self.fque[i][1]
				del self.fque[i]
				self.fque.append([f, b])
				break
		return


	def bias(self):
		r1 = int(math.ceil(random.random()*maxCacheSlots))-1
		r2 = int(math.ceil(random.random()*maxCacheSlots))-1

		a = self.cache[r1][2]
		b = self.cache[r2][2]

		if a > b:
			self.cache[r1] = [self.fname, self.block, 0]
		else:
			self.cache[r2] = [self.fname, self.block, 0]		
		return


	def unif(self):
		r = int(math.ceil(random.random()*maxCacheSlots))-1
		self.cache[r] = [self.fname, self.block, 0]
		
		return


	def mcd(self):
		waitque[self.l].append([self.fname, self.tname, self.l-1, self.hopCount, self.arriveTime, self.block])
		for i in range(maxCacheSlots):
			if self.cache[i][0] == self.fname and self.cache[i][1] == self.block:
				self.cache[i] = [None, None, 0]
				break
		for i in range(len(self.fque)):
			if self.fque[i][0] == self.fname and self.fque[i][1] == self.block:
				del self.fque[i]
				break
		return


	def lcd(self):
		waitque[self.l].append([self.fname, self.tname, self.l-1, self.hopCount, self.arriveTime, self.block])
		return


	def storCache(self):
		for i in range(maxCacheSlots):
			if self.cache[i][0] == None:
				self.cache[i] = [self.fname, self.block, 0]
				self.fque.append([self.fname, self.block])
				return
		
		#キャッシュ廃棄
		#self.fifo()
		#self.unif()
		#self.bias()

		return


	def fCache(self):
		for i in range(maxCacheSlots):
			if t2[self.l-1].cache[i][0] == self.fname and t2[self.l-1].cache[i][1] == self.block:
				return i
		return -1


	def recQue(self):
		if recque[self.l] != []:
			self.fname, self.tname, self.dest, self.hopCount, self.arriveTime, self.block = recque[self.l][0]
			if self.dest >= 1:
				if self.dest==self.l:
					if self.findCache() == -1:
						self.storCache()
						a = recque[self.l].pop(0)
					else:
						a = recque[self.l].pop(0)
				else:
					waitque[self.l].append(recque[self.l].pop(0))
			elif self.dest == -1:
				waitque[self.l].append(recque[self.l].pop(0))

			else:
				bb = self.findCache()
				if bb == -1:
					self.chk=1
					recque[self.l][0][3] += 1
					recque[self.l+1].append(recque[self.l].pop(0))
				else:
					waitque[self.l].append([self.fname, self.tname, -1, self.hopCount, self.arriveTime, self.block])
					self.cache[bb][2] += 1
					a = recque[self.l].pop(0)

					self.lru()
					if self.l != 1:
						if self.fCache() < 0:
							self.mcd()
							#self.lcd()
		return


	def sendQue(self):
		self.locks0=1
		self.fname, self.tname, self.dest, self.hopCount, self.arriveTime, self.block = waitque[self.l][0]

		if self.dest==-1:
			with ifque[self.sc].request() as req:
				yield req
				for i in range(self.count):
					if i%ls[self.h][4] == 0 and self.dest == -1:
						yield self.env.timeout(self.delay)
					yield self.env.timeout(self.wait)
				if self.l==1:
					a = waitque[self.l].pop(0)
					fcount[self.tname][0] += 1
					fcount[self.tname][1] += self.hopCount
					if fcount[self.tname][0] == devide:
						self.c += 1
						a.append(self.env.now) #終了時間
						endque.append(a)
						endque[-1].append(fcount[self.tname][0])
						endque[-1].append(fcount[self.tname][1])
						#print("downloaded:  ", self.tname, self.fname, self.env.now)
						#if self.c % 40 == 0: 
						#	show()
						#sys.stdout.flush()
				else:
					recque[self.l-1].append(waitque[self.l].pop(0))
				self.locks0 = 0
		else:
			recque[self.l-1].append(waitque[self.l].pop(0))

		return


	def findCache(self):
		for i in range(maxCacheSlots):
			if self.cache[i][0] == self.fname and self.cache[i][1] == self.block:
				return i
		return -1


	def retr(self):
		while True:
			yield self.env.timeout(1000)	
			self.recQue()
			if waitque[self.l] != [] and self.locks0 == 0:
				yield self.env.process(self.sendQue())
			else:
				self.locks0=0

def show():
	l = len(endque)
	sumHopCount = 0
	averageMoth = devide*l
	min, max, sumTime = 10**10, 0.0, 0.0

	for fname, tname, dest, hopCount, arriveTime, block, endTime, cc, totalHopCount in endque:
		sumHopCount += totalHopCount
		#perform = fileSize/ (endTime-arriveTime)
		sumTime += (endTime-arriveTime)
		min = (endTime-arriveTime) if (endTime-arriveTime)<min else min
		max = (endTime-arriveTime) if (endTime-arriveTime)>max else max
	averageHopCount = sumHopCount/averageMoth

	print("================================================================")
	print("Number of transaction:  ", l)
	print("Number of Contets:  ", contentNum)
	print("File size[MBytes]:  ", fileSize/(10**6))
	print("Chunk size[KBytes]:  ", chunkSize/10**3)
	print("Cache size[MBytes]:  ", maxCacheSlots*chunkSize/10**6)
	print("Path length(Terminal - CMS):  ", maxCacheNumber+1)
	print("Number of chunks:  ", averageMoth)
	print("Total hopcount:  ", sumHopCount)
	print("Average hopcount:  ", averageHopCount)
	print("time[s]: mean/min/max:  %8.2f / %8.2f / %8.2f" % (sumTime/l/10**6, min/10**6, max/10**6))
	print("Total time[s]:  %8.2f" %(sumTime/10**6))
	print("Total ratio[MB/S]:  %10.6f" %(l*fileSize/sumTime))
	print("================================================================")


	l = len(endque)
	sumHopCount = 0
	averageMoth = devide*l
	min, max, sumTime, n = 10**10, 0.0, 0.0, 0 

	for fname, tname, dest, hopCount, arriveTime, block, endTime, cc, totalHopCount in endque:
		if fname == 'f1':
			n+=1
			sumHopCount += totalHopCount
			sumTime += (endTime-arriveTime)
			min = (endTime-arriveTime) if (endTime-arriveTime)<min else min
			max = (endTime-arriveTime) if (endTime-arriveTime)>max else max
	averageHopCount = sumHopCount/(n*devide)

	print("================================================================")
	print("Number of transaction:  ", n)
	print("Sample FileName:  f01")
	print("Number of chunks:  ", n*devide)
	print("Total hopcount:  ", sumHopCount)
	print("Average hopcount:  ", averageHopCount)
	print("time[s]: mean/min/max:  %8.2f / %8.2f / %8.2f" % (sumTime/n/10**6, min/10**6, max/10**6))
	print("Total time[s]:  %8.2f" %(sumTime/10**6))
	print("Total ratio[MB/S]:  %10.6f" %(n*fileSize/sumTime))
	print("================================================================")



	l = len(endque)
	sumHopCount = 0
	averageMoth = devide*l
	min, max, sumTime, n = 10**10, 0.0, 0.0, 0

	for fname, tname, dest, hopCount, arriveTime, block, endTime, cc, totalHopCount in endque:
		if fname != 'f1':
			n+=1
			sumHopCount += totalHopCount
			sumTime += (endTime-arriveTime)
			min = (endTime-arriveTime) if (endTime-arriveTime)<min else min
			max = (endTime-arriveTime) if (endTime-arriveTime)>max else max
	averageHopCount = sumHopCount/(n*devide)

	print("================================================================")
	print("Number of transaction:  ", n)
	print("Sample FileName:  not f01")
	print("Number of chunks:  ", n*devide)
	print("Total hopcount:  ", sumHopCount)
	print("Average hopcount:  ", averageHopCount)
	print("time[s]: mean/min/max:  %8.2f / %8.2f / %8.2f" % (sumTime/n/10**6, min/10**6, max/10**6))
	print("Total time[s]:  %8.2f" %(sumTime/10**6))
	print("Total ratio[MB/S]:  %10.6f" %(n*fileSize/sumTime))
	print("================================================================")



def main():
	env = simpy.Environment()
	initCache(env)	
	tevent = makeEvent(720) #0.2hz

	for (term, fname, arrivaltime) in tevent:
		t[term] = Tran(env, term, fname, arrivaltime)

	for i in range(maxCacheNumber):
		na = i+1
		mm = 'c' + str(na)
		t2[na] = cacheServ(env, cache, na, mm)

	mm = 'c' + str(na+1)
	t2[na+1] = cmsServ(env, na+1, mm)

	env.run(until=simulationTime *2)
	show()

if __name__ == '__main__':
	main()
