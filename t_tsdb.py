import unittest
import os

from tsdb import *

TESTDB = "tsdb_test"

def nuke_testdb():
    os.system("rm -rf " + TESTDB)

class CreateTSDB(unittest.TestCase):
    def testCreate(self):
        """can we create a db?"""
        try:
            TSDB.create(TESTDB)
        except:
            self.fail("unable to create db")

        if not os.path.isdir(TESTDB):
            self.fail("directory doesn't exist")

        if not os.path.isfile(os.path.join(TESTDB,"TSDB")):
            self.fail("metadata file TSDB doesn't exist")

    def testRecreate(self):
        """does trying to create the same db again fail?"""
        TSDB.create(TESTDB)
        self.assertRaises(TSDBAlreadyExistsError, TSDB.create, TESTDB)

    def tearDown(self):
        nuke_testdb()

class CreateTSDBSet(unittest.TestCase):
    def setUp(self):
        self.db = TSDB.create(TESTDB)

    def tearDown(self):
        nuke_testdb()

    def doCreate(self, name):
        try:
            self.db.add_set(name)
        except Exception, e:
            print e.__class__.__name__, e
            self.fail(e)

        if not os.path.isdir(os.path.join(TESTDB,name)):
            self.fail("directory doesn't exist")

        if not os.path.isfile(os.path.join(TESTDB, name, "TSDBSet")):
            self.fail("metadata file TSDBSet doesn't exist")

    def testCreate(self):
        """can we create a TSDBSet?"""
        self.doCreate("foo")

    def testPathCreate(self):
        """can we create TSDBSet hierarchy?"""
        self.doCreate("blort/foo/bar")

    def testRecreate(self):
        self.db.add_set("foo")
        self.assertRaises(TSDBNameInUseError, self.db.add_set, "foo")

class CreateTSDBVar(unittest.TestCase):
    def setUp(self):
        self.db = TSDB.create(TESTDB)

    def tearDown(self):
        nuke_testdb()

    def doCreate(self, name):
        try:
            self.db.add_var(name, Counter32, 60, YYYYMMDDChunkMapper)
        except Exception, e:
            self.fail(e)

        if not os.path.isdir(os.path.join(TESTDB, name)):
            self.fail("directory doesn't exist")

        if not os.path.isfile(os.path.join(TESTDB, name, "TSDBVar")):
            self.fail("metadata file TSDBVar doesn't exist")

    def testCreate(self):
        """can we create a TSDBVar?"""
        self.doCreate("bar")

    def testPathCreate(self):
        """can we create a TSDBVar inside a TSDBSet?"""
        self.doCreate("baz/foo/bar")

    def testRecreate(self):
        self.db.add_var("bar", Counter32, 60, YYYYMMDDChunkMapper)
        self.assertRaises(TSDBNameInUseError, self.db.add_var, "bar", Counter32, 60, YYYYMMDDChunkMapper)

class TestData(unittest.TestCase):
    ts = 1184863723
    step = 60

    def setUp(self):
        self.db = TSDB.create(TESTDB)
        
    def tearDown(self):
        nuke_testdb()

    def testData(self):
        for t in TYPE_MAP[1:]:
            for m in CHUNK_MAPPER_MAP[1:]:
                vname = "%s_%s" % (t,m)
                var = self.db.add_var(vname, t, self.step, m)
                name = m.name(self.ts)
                begin = m.begin(name)
                size = m.size(name, t.size, self.step)
                
                r = range(0, (size/t.size) * self.step, self.step)

                # write a full chunk of data
                for i in r:
                    v = t(begin+i, ROW_VALID, i)
                    var.insert(v)

                # see if the file is the right size
                f = os.path.join(TESTDB, vname, name)
                if os.stat(f).st_size != size:
                    raise "chunk is wrong size:"

                # read each value to check that the data got written correctly
                for i in r:
                    v = var.select(begin+i)
                    if v.value != i:
                        raise "data bad at %s", str(i) + " " + str(begin+i) + " " + str(v)

                low = begin-1
                if m.name == m.name(low):
                    raise "lower chunk boundary is incorrect"

                high = begin + ((size/t.size)*self.step) + 1
                if m.name == m.name(high):
                    raise "upper chunk boundary is incorrect"

                for i in (low,high):
                    var.insert( t(i, ROW_VALID, i) )
                    if var.select(i).value != i:
                        raise "incorrect value at " + str(i)

                    f = os.path.join(TESTDB, vname, m.name(i))
                    if os.stat(f).st_size != m.size(m.name(i), t.size,
                            self.step):
                        raise "chunk is wrong size at: " + str(i)


        
if __name__ == "__main__":
    print "these tests create large files, it may take a bit for them to run"
    nuke_testdb() 
    unittest.main()
