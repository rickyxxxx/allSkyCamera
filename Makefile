EXEC = SingleFrameMode
SHARED_MODE=0

COMP_INC1 = /usr/include/
COMP_INC2 = /usr/local/include/
COMP_LIB = /usr/local/lib/
QHY_LIB  = /usr/local/lib/libqhyccd.so

CXX = g++
CXXFLAGS = -Wall -Wsign-compare -std=c++11 -I. -I $(COMP_INC1)  -I $(COMP_INC2)
EXTRALIBS = -Wl,${QHY_LIB} -lusb-1.0 -pthread
OPENCV = -L/usr/local/lib -lopencv_core -lopencv_imgproc

CP = cp -f

OBJA = $(EXEC).o


all: $(EXEC) 

.cpp.o:
	$(CXX) $(CXXFLAGS) -c -o $@ $<


$(EXEC): $(OBJA) 
	$(CXX) -o SingleFrameMode $(OBJA) $(EXTRALIBS) $(OPENCV)

install:
#	$(CP) $(EXEC)

clean:
	-$(RM) $(EXEC)
	-$(RM) *.o
	-$(RM) *~
	-$(RM) *.orig
