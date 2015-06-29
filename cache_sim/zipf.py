# -*- coding: utf-8 -*-


u"""
math.ceil(math.e**((math.log(N+math.e**-0.5772156649)+0.5772156649)*x-0.5772156649)-math.e**-0.5772156649)))))
x=[0,1]

zipfMandelbrot
	f(x) = c / (x+b)^a 
	PDF
	f(x) = 1/x

def zipf(max):
	return math.e ** (random.random() * math.log(max+1.0)) - 1.0)))))))

"""



import pylab
import random
import math



def zipf(max, count):
	ss=0
	cc=0
	data=list()
	lis=list()

	for i in range(1, max+1):
		ss = (1/(i**1.0))   +ss
	
	for i in range(1, max+1):
		cc = cc + 1/(i**1.0)/ss
		lis.append(cc)

	for j in range(count):
		r = random.random()
		for i in range(max):
			if r < lis[i]:
				#return i
				data.append(i)
				break
	return data
	

def zipf_plot(max):	
	ss=0
	cc=0
	aa=0
	lis=list()
	data = list()
	lis2=list()


	for i in range(1, max+1):
		ss = (1/(i**1.0))   +ss
		#lis.append(ss)

	aa=0
	lis2=list()
	for i in range(1, max+1):
		aa = (1/(i**1.5))   +aa
		#lis2.append(aa)

	for i in range(1, max+1):
		cc = cc + 1/(i**1.0)/ss
		lis.append(cc)

	cc=0
	for i in range(1, max+1):
		cc = cc + 1/(i**1.5)/aa
		lis2.append(cc)
	
	x = pylab.arange(1, max+1, 1)
	pylab.figure(figsize=(8, 6), dpi=80, facecolor="white")
	pylab.plot(x, lis, "+", label=u"Zipf a=1.0")
	pylab.plot(x, lis2, ".", label=u"Zipf a=1.5")
	pylab.xlabel("ranking")
	pylab.ylabel("frequently")
	pylab.legend(loc = "lower right")
	#pylab.grid(True)
	pylab.show()


if __name__ == '__main__':
	zipf_plot(300)
