import os

######################################################################
## 
## Feature Broker
##  
######################################################################

class FeatureBroker:
    def __init__(self, allowReplace=False):
        self.providers = {}
        self.allowReplace = allowReplace
    def Provide(self, feature, provider, *args, **kwargs):
        if not self.allowReplace:
            assert not self.providers.has_key(feature), "Duplicate feature: %r" % feature
        if callable(provider):
            def call(): return provider(*args, **kwargs)
        else:
            def call(): return provider
        self.providers[feature] = call
    def __getitem__(self, feature):
        try:
            provider = self.providers[feature]
        except KeyError:
            raise AttributeError, "Unknown feature named %r" % feature
        return provider()


features = FeatureBroker()

######################################################################
## 
## Representation of Required Features and Feature Assertions
## 
######################################################################

#
# Some basic assertions to test the suitability of injected features
#

def NoAssertion(): 
    def test(obj): return True
    return test

def IsInstanceOf(*classes):
    def test(obj): return isinstance(obj, classes)
    return test

def HasAttributes(*attributes):
    def test(obj):
        for each in attributes:
            if not hasattr(obj, each): return False
        return True
    return test

def HasMethods(*methods):
    def test(obj):
        for each in methods:
            try:
                attr = getattr(obj, each)
            except AttributeError:
                return False
            if not callable(attr): return False
        return True
    return test

#
# An attribute descriptor to "declare" required features
#

class DataAttribute(object):
    """A data descriptor that sets and returns values
       normally and notifies on value changed.
    """

    def __init__(self, initval=None, name='var'):
        self.val = initval
        self.name = name

    def __get__(self, obj, objtype):
        return self.val

    def __set__(self, obj, val):
        self.val = val
        for handler in obj.observers:
            handler()


class RequiredFeature(object):
    def __init__(self, feature, assertion=NoAssertion()):
        self.feature = feature
        self.assertion = assertion
        self.result=None
    def __get__(self, obj, T):
        self.result = self.Request(obj)
        return self.result # <-- will request the feature upon first call
    def __getattr__(self, name):
        assert name == 'result', "Unexpected attribute request other then 'result'"
        return self.result
    def Request(self, callee):
        obj = features[self.feature]
        try:
            #handler = getattr(callee, ("on_%s_change" % self.feature).lower())
            #handler = callee.update
            obj.register_handler(callee)
        except AttributeError:
            pass
            
        assert self.assertion(obj), \
                 "The value %r of %r does not match the specified criteria" \
                 % (obj, self.feature)
        return obj

class Component(object):
    "Symbolic base class for components"
    def __init__(self):
        self.observers = []
    
    @staticmethod    
    def _rm_duplicate_deps(deps):
        for i, d in enumerate(deps):
            if d in deps[i+1:]: del deps[i]
        return deps
    
    def get_dependencies(self):
        deps = [o.get_dependencies() for o in self.observers]
        deps = sum(deps, self.observers)
        deps = Component._rm_duplicate_deps(deps)
        return deps
    
    def register_handler(self, handler):
        if handler not in self.observers:
            self.observers.append(handler)
    def unregister_handler(self, handler):
        if handler in self.observers:
            self.observers.remove(handler)
    def notify_observers(self):
        for dep in self.get_dependencies():
            dep._update() 
                       
    def _update(self):
        pass
    
    def update(self):
        self._update()
        self.notify_observers()

class dictproperty(object):
    """implements collection properties with dictionary-like access.
    Adapted from `Active State Recipe 440514:
    <http://code.activestate.com/recipes/440514-dictproperty-properties-for-dictionary-attributes/>`_
    """

    class _proxy(object):

        def __init__(self, obj, fget, fset, fdel):
            self._obj = obj
            self._fget = fget
            self._fset = fset
            self._fdel = fdel

        def __getitem__(self, key):
            if self._fget is None:
                raise TypeError, "can't read item"
            return self._fget(self._obj, key)

        def __setitem__(self, key, value):
            if self._fset is None:
                raise TypeError, "can't set item"
            self._fset(self._obj, key, value)

        def __delitem__(self, key):
            if self._fdel is None:
                raise TypeError, "can't delete item"
            self._fdel(self._obj, key)

    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self._fget = fget
        self._fset = fset
        self._fdel = fdel
        self.__doc__ = doc

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return self._proxy(obj, self._fget, self._fset, self._fdel)

class Zoomer(object):
    '''Allows to zoom subplots'''
    def __init__(self, plt, fig):
        self.axlist=[]
        self.geometry=[]
        plt.connect('key_press_event', self.zoom)
        self.fig=fig
    
    def zoom(self, event):
        axis=event.inaxes
        
        if axis==None or event.key!='z':
            return
        
        if axis.get_geometry() == (1,1,1):
            zoomed=True
        else:
            zoomed=False
        
        if zoomed==False:
            self.geometry.append(axis.get_geometry())
            self.axlist=list(self.fig.get_axes())
            for ax in self.axlist:
                self.fig.delaxes(ax)
      
            axis.change_geometry(1,1,1)
            self.fig.add_axes(axis)
            self.fig.show()
            
        else:
            self.fig.delaxes(axis)
            for ax in self.axlist:
                self.fig.add_axes(ax)
            geom = self.geometry.pop()
            axis.change_geometry(*geom)
            axis.autoscale()
            self.fig.show()


######################################################################
## 
## DEMO
## 
######################################################################

# ---------------------------------------------------------------------------------
# Some python module defines a Bar component and states the dependencies
# We will assume that
# - Console denotes an object with a method WriteLine(string)
# - AppTitle denotes a string that represents the current application name
# - CurrentUser denotes a string that represents the current user name
#

