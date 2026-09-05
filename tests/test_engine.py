from dataclasses import replace
import random
from market.engine import *

def tiny(**kw):
    base=Zone("a","A",1,100,200,150,20,0,"#fff",True,5)
    return replace(base,**kw)
def req(i, **kw): return Request(str(i),2,("a",),**kw)

def test_inventory_never_oversold_and_adjacency():
    a,_=allocate([req(i) for i in range(20)],[tiny()],seed=1)
    assert sum(x.quantity for x in a)<=20
    assert all(x.quantity==2 for x in a)
def test_adjacency_rejects_larger_group_than_block():
    a,f=allocate([Request("x",4,("a",))],[tiny(block_size=3)],seed=1)
    assert not a and f
def test_vip_consumes_underlying_inventory():
    a,_=allocate([req("vip",vip=True),req("std")],[tiny(capacity=2)],seed=1)
    assert len(a)==1 and sum(x.quantity for x in a)==2
def test_prices_inside_bounds():
    assert validate_prices([tiny(price=201)])
    assert not validate_prices([tiny()])
def test_rational_price_architecture():
    assert validate_prices([tiny(id="best",price=100),tiny(id="bad",name="Bad",rank=2,price=150)])
def test_unselected_product_forbidden():
    a,f=allocate([Request("x",2,("missing",))],[tiny()])
    assert not a and f
def test_timestamp_and_order_do_not_matter():
    rs=[req(i,timestamp=i) for i in range(30)]
    a,_=allocate(rs,[tiny()],seed=9); random.Random(3).shuffle(rs)
    rs=[replace(r,timestamp=999-r.timestamp) for r in rs]
    b,_=allocate(rs,[tiny()],seed=9)
    assert {(x.fan_id,x.zone) for x in a}=={(x.fan_id,x.zone) for x in b}
def test_cohort_priority_honored():
    a,_=allocate([req("ordinary"),req("loyal",cohorts=("fan_club",))],[tiny(capacity=2)],seed=1)
    assert a[0].fan_id=="loyal"
def test_sponsor_minimum_honored():
    a,_=allocate([req("ordinary"),req("card",cohorts=("sponsor",))],[tiny(capacity=2)],seed=1,sponsor_min=2)
    assert a[0].fan_id=="card" and "sponsor" in a[0].reason
def test_ticket_limit_and_duplicate_rule():
    r=Request("same",9,("a",),fewer_ok=True)
    a,_=allocate([r,r],[tiny(capacity=10)],ticket_limit=4)
    assert len(a)==1 and a[0].quantity==4
def test_seed_reproducibility():
    assert synthetic_summary(3,100)==synthetic_summary(3,100)
def test_negotiation_prices_are_catalog_prices():
    z=[tiny(),tiny(id="b",name="B",rank=2,price=110)]
    p=negotiate(req("x"),z,{"b":10})
    assert all(x["unit_price"] in {q.price for q in z} for x in p)
def test_hidden_wtp_does_not_change_price():
    a,_=allocate([req("low",latent_wtp=1),req("high",latent_wtp=9999)],[tiny(capacity=4)])
    assert {x.unit_price for x in a}=={150}

