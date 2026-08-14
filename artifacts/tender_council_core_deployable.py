# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from dataclasses import dataclass
import datetime
import hashlib
import json
from genlayer import*
A='DRAFT'
B='OPEN'
C='CLOSED'
D='EVALUATING'
E='EVALUATION_RETRYABLE'
F='EVALUATION_FAILED'
G='PROVISIONAL_AWARD'
H='RESPONSE_WINDOW'
I='REVIEWING_CHALLENGES'
J='REVIEW_RETRYABLE'
K='AWARDED'
L='SETTLEMENT_PENDING'
M='SETTLED'
N='NO_VALID_BID'
O='CANCELLED'
P='REFUND_PENDING'
Q='ESCROWED'
R='UNSETTLED'
S='TRANSFER_PENDING'
T='SETTLED'
U='REFUND_PENDING'
V='ADMITTED'
W='MANDATORY_REQUIREMENT_MISAPPLIED'
X='COMMITTED_EVIDENCE_OVERLOOKED'
Y='RUBRIC_MISAPPLIED'
Z='EVIDENCE_INTEGRITY_ERROR'
AA=(W,X,Y,Z)
AB='tendercouncil.core.v2'
AC='tendercouncil.evaluator.v2'
AD='tendercouncil.snapshot.v1'
AE=600
AF=21600
AG=3
AH=21600
AI=3
AJ=96
AK=200
AL=512
AM=4000
AN=32
AO=16
AP=12000
AQ=Address('0x'+'0'*40)
def AR(v:str)->str:
    return 'sha256:'+hashlib.sha256(v.encode('utf-8')).hexdigest()
def AS(v:str)->bool:
    if len(v)!=71 or v[:7]!='sha256:':
        return False
    for char in v[7:]:
        if char not in '0123456789abcdef':
            return False
    return True
def AT(v)->str:
    return json.dumps(v,sort_keys=True,separators=(',',':'))
def AU(v:str):
    e=('technical','delivery','price','capability','support')
    g={}
    for i in v.split(';'):
        parts=i.split('=')
        if len(parts)!=2 or parts[0]in g:
            raise ValueError('malformed rubric')
        g[parts[0]]=int(parts[1])
    if tuple(sorted(g))!=tuple(sorted(e)):
        raise ValueError('malformed rubric')
    weights=tuple((g[h]for h in e))
    if sum(weights)!=100:
        raise ValueError('rubric must total 100')
    return weights
def AV(v:str)->bool:
    if len(v)>AP:
        return False
    if v=='':
        return True
    seen=[]
    for i in v.split(';'):
        fields=i.split('|')
        if len(fields)!=6:
            return False
        evidence_id,k,criterion,d,url,digest=fields
        if evidence_id=='' or evidence_id in seen or len(evidence_id)>AJ:
            return False
        if k not in('CAPABILITY','DELIVERY','SUPPORT','TECHNICAL'):
            return False
        if criterion not in('capability','delivery','support','technical'):
            return False
        if d not in('0','1')or not url.startswith('https://'):
            return False
        if not AS(digest):
            return False
        seen.append(evidence_id)
    return True
@allow_storage
@dataclass
class CoreTender:
    tender_id:str
    buyer:Address
    title:str
    brief_url:str
    brief_sha256:str
    max_budget_wei:u256
    max_delivery_days:u64
    min_support_days:u64
    bidding_deadline:u64
    response_window_seconds:u64
    status:str
    requirements:str
    rubric:str
    evidence_policy:str
    escrow_deposited:u256
    closed_snapshot_digest:str
    evaluation_nonce:u64
    evaluation_timeout_at:u64
    evaluation_result_digest:str
    provisional_winner:str
    final_winner:str
    response_window_start:u64
    response_window_end:u64
    review_nonce:u64
    review_timeout_at:u64
    challenge_set_digest:str
    settlement_state:str
    winner_payout_amount:u256
    buyer_refund_amount:u256
    payout_pending:bool
    refund_pending:bool
    payout_confirmed:bool
    refund_confirmed:bool
    refund_kind:str
@allow_storage
@dataclass
class CoreBid:
    bid_id:str
    tender_id:str
    bidder:Address
    price_wei:u256
    delivery_days:u64
    support_days:u64
    proposal_url:str
    proposal_sha256:str
    evidence_commitments:str
    schema_version:str
    submitted_at:u64
@allow_storage
@dataclass
class CoreChallenge:
    challenge_id:str
    tender_id:str
    challenger:Address
    reason_code:str
    target_bid_id:str
    referenced_evidence_id:str
    challenge_url:str
    challenge_sha256:str
    submitted_at:u64
    status:str
    claims:str
@gl.contract_interface
class AX:
    class View:
        def get_evaluation_result(self,tender_id:str,nonce:u64)->str:
            ...
        def get_review_result(self,tender_id:str,nonce:u64)->str:
            ...
    class Write:
        def start_evaluation_job(self,tender_id:str,nonce:u64,snapshot_digest:str):
            ...
        def start_review_job(self,tender_id:str,evaluation_nonce:u64,review_nonce:u64,snapshot_digest:str,result_digest:str,challenge_set_digest:str):
            ...
@gl.evm.contract_interface
class AY:
    class View:
        pass
    class Write:
        pass
class TenderCouncilCore(gl.Contract):
    tenders:TreeMap[str,CoreTender]
    bids:TreeMap[str,CoreBid]
    challenges:TreeMap[str,CoreChallenge]
    tender_ids:DynArray[str]
    bid_ids:DynArray[str]
    challenge_ids:DynArray[str]
    bootstrapper:Address
    evaluator_address:Address
    evaluator_version:str
    evaluator_code_hash:str
    evaluator_bound:bool
    total_locked_escrow:u256
    financial_outflow_pending:bool
    financial_outflow_tender_id:str
    financial_outflow_kind:str
    financial_outflow_amount:u256
    financial_outflow_balance_before:u256
    def __init__(self):
        self.bootstrapper=gl.message.sender_address
        self.evaluator_address=AQ
        self.evaluator_version=''
        self.evaluator_code_hash=''
        self.evaluator_bound=False
        self.total_locked_escrow=u256(0)
        self.financial_outflow_pending=False
        self.financial_outflow_tender_id=''
        self.financial_outflow_kind=''
        self.financial_outflow_amount=u256(0)
        self.financial_outflow_balance_before=u256(0)
    def a(self)->u64:
        return u64(int(datetime.datetime.now(datetime.timezone.utc).timestamp()))
    def b(self,v:str,maximum:int,z:str):
        if v=='' or len(v)>maximum:
            raise AW(z+' is empty or exceeds its bound')
    def c(self,v:str,z:str):
        self.b(v,AL,z)
        if not v.startswith('https://'):
            raise AW(z+' must use https')
    def d(self,t:CoreTender):
        if gl.message.sender_address!=t.buyer:
            raise AW('only the tender buyer may perform this action')
    def e(self):
        if not self.evaluator_bound:
            raise AW('evaluator binding is incomplete')
    def f(self):
        if self.financial_outflow_pending:
            raise AW('another financial outflow is pending')
    def g(self,tender_id:str,k:str,a:u256):
        self.f()
        if a==u256(0)or self.balance<a:
            raise AW('escrow balance is insufficient')
        self.financial_outflow_pending=True
        self.financial_outflow_tender_id=tender_id
        self.financial_outflow_kind=k
        self.financial_outflow_amount=a
        self.financial_outflow_balance_before=self.balance
    def h(self):
        self.financial_outflow_pending=False
        self.financial_outflow_tender_id=''
        self.financial_outflow_kind=''
        self.financial_outflow_amount=u256(0)
        self.financial_outflow_balance_before=u256(0)
    def i(self,t:CoreTender,k:str):
        self.f()
        if t.settlement_state!=R:
            raise AW('failed process escrow is not refundable')
        t.winner_payout_amount=u256(0)
        t.buyer_refund_amount=t.escrow_deposited
        if t.buyer_refund_amount!=t.escrow_deposited:
            raise AW('failed process refund invariant failed')
        t.refund_pending=True
        t.refund_kind=k
        self.g(t.tender_id,k,t.buyer_refund_amount)
        AY(t.buyer).emit_transfer(value=t.buyer_refund_amount,on='finalized')
        t.status=P
        t.settlement_state=U
        self.tenders[t.tender_id]=t
    def j(self,tender_id:str)->CoreTender:
        t=self.tenders.get(tender_id)
        if t is None:
            raise AW('tender does not exist')
        return t
    def k(self,t:CoreTender):
        if int(t.evaluation_nonce)>=AG:
            raise AW('maximum evaluation attempts reached')
        t.evaluation_nonce=t.evaluation_nonce+u64(1)
        n=self.a()
        t.evaluation_timeout_at=n+u64(AF)
        t.status=D
        self.tenders[t.tender_id]=t
        AX(self.evaluator_address).emit(on='finalized').start_evaluation_job(t.tender_id,t.evaluation_nonce,t.closed_snapshot_digest)
    def l(self,t:CoreTender):
        if int(t.evaluation_nonce)>=AG:
            t.status=F
            t.settlement_state=R
        else:
            t.status=E
    def m(self,t:CoreTender):
        if int(t.review_nonce)>=AI:
            raise AW('maximum review attempts reached')
        t.review_nonce=t.review_nonce+u64(1)
        n=self.a()
        t.review_timeout_at=n+u64(AH)
        t.status=I
        self.tenders[t.tender_id]=t
        AX(self.evaluator_address).emit(on='finalized').start_review_job(t.tender_id,t.evaluation_nonce,t.review_nonce,t.closed_snapshot_digest,t.evaluation_result_digest,t.challenge_set_digest)
    def n(self,t:CoreTender):
        if int(t.review_nonce)>=AI:
            if t.provisional_winner=='':
                raise AW('review fallback has no provisional winner')
            t.final_winner=t.provisional_winner
            t.status=K
            t.settlement_state=R
        else:
            t.status=J
    def o(self,tender_id:str)->str:
        t=self.j(tender_id)
        bid_values=[]
        for bid_id in sorted(self.bid_ids):
            b=self.bids[bid_id]
            if b.tender_id!=tender_id:
                continue
            bid_values.append({'bid_id':str(b.bid_id),'bidder':str(b.bidder),'price_wei':int(b.price_wei),'delivery_days':int(b.delivery_days),'support_days':int(b.support_days),'proposal_url':str(b.proposal_url),'proposal_sha256':str(b.proposal_sha256),'evidence_commitments':str(b.evidence_commitments),'schema_version':str(b.schema_version),'submitted_at':int(b.submitted_at)})
        return AT({'schema_version':AD,'tender_id':str(t.tender_id),'buyer':str(t.buyer),'title':str(t.title),'brief_url':str(t.brief_url),'brief_sha256':str(t.brief_sha256),'max_budget_wei':int(t.max_budget_wei),'max_delivery_days':int(t.max_delivery_days),'min_support_days':int(t.min_support_days),'bidding_deadline':int(t.bidding_deadline),'response_window_seconds':int(t.response_window_seconds),'requirements':str(t.requirements),'rubric':str(t.rubric),'evidence_policy':str(t.evidence_policy),'bids':bid_values})
    def p(self,tender_id:str)->str:
        y=[]
        for challenge_id in sorted(self.challenge_ids):
            c=self.challenges[challenge_id]
            if c.tender_id!=tender_id:
                continue
            y.append({'challenge_id':str(c.challenge_id),'challenger':str(c.challenger),'reason_code':str(c.reason_code),'target_bid_id':str(c.target_bid_id),'referenced_evidence_id':str(c.referenced_evidence_id),'challenge_url':str(c.challenge_url),'challenge_sha256':str(c.challenge_sha256),'submitted_at':int(c.submitted_at)})
        return AR(AT({'schema_version':'tendercouncil.challenges.v1','items':y}))
    def q(self,t:CoreTender,r:dict,result_type:str):
        d=('confidence','deterministic_disqualified_bid_ids','integrity_disqualified_bid_ids','semantic_candidate_ids','semantic_disqualified_bid_ids','semantic_classifications','disqualified_bid_ids','runner_up_bid_id','runner_up_score','rationale','scores','valid_bid_ids','winner_bid_id','winner_total_score','status')
        if not isinstance(r,dict)or tuple(sorted(r))!=tuple(sorted(d)):
            raise AW('malformed evaluator result')
        if r['status']!=result_type:
            raise AW('result type mismatch')
        x=r['valid_bid_ids']
        disqualified=r['disqualified_bid_ids']
        category_fields=('deterministic_disqualified_bid_ids','integrity_disqualified_bid_ids','semantic_candidate_ids','semantic_disqualified_bid_ids')
        if not isinstance(x,list)or not isinstance(disqualified,list)or any((not isinstance(r[z],list)for z in category_fields)):
            raise AW('result bid sets are malformed')
        all_ids=set()
        for bid_id in self.bid_ids:
            if self.bids[bid_id].tender_id==t.tender_id:
                all_ids.add(bid_id)
        deterministic=set()
        for bid_id in all_ids:
            b=self.bids[bid_id]
            if b.price_wei>t.max_budget_wei or b.delivery_days>t.max_delivery_days or b.support_days<t.min_support_days or(b.submitted_at>t.bidding_deadline)or(b.schema_version!='tendercouncil.bid.v1'):
                deterministic.add(bid_id)
        if set(r['deterministic_disqualified_bid_ids'])!=deterministic:
            raise AW('deterministic disqualification mismatch')
        integrity=set(r['integrity_disqualified_bid_ids'])
        if not integrity.issubset(all_ids)or integrity&deterministic:
            raise AW('integrity disqualification mismatch')
        semantic_candidates=all_ids-deterministic-integrity
        if set(r['semantic_candidate_ids'])!=semantic_candidates:
            raise AW('semantic candidate set mismatch')
        classifications=r['semantic_classifications']
        if not isinstance(classifications,list)or len(classifications)!=len(semantic_candidates):
            raise AW('semantic classification coverage mismatch')
        classified={}
        for i in classifications:
            if not isinstance(i,dict)or tuple(sorted(i))!=('bid_id','mandatory_requirements_pass')or i['bid_id']in classified or(i['bid_id']not in semantic_candidates)or(not isinstance(i['mandatory_requirements_pass'],bool)):
                raise AW('malformed semantic classification')
            classified[i['bid_id']]=i['mandatory_requirements_pass']
        semantic_bad={bid_id for bid_id in semantic_candidates if not classified[bid_id]}
        if set(r['semantic_disqualified_bid_ids'])!=semantic_bad:
            raise AW('semantic disqualification mismatch')
        expected_valid=semantic_candidates-semantic_bad
        expected_disqualified=deterministic|integrity|semantic_bad
        if set(x)!=expected_valid or set(disqualified)!=expected_disqualified:
            raise AW('result bid partition is invalid')
        if not isinstance(r['rationale'],str)or len(r['rationale'])>AM:
            raise AW('result rationale is malformed')
        if r['confidence']not in('HIGH','MEDIUM','LOW'):
            raise AW('result confidence is malformed')
        if result_type=='NO_VALID_BID':
            if r['winner_bid_id']!='' or x or r['scores']or(r['winner_total_score']!=0)or(r['runner_up_bid_id']!='')or(r['runner_up_score']!=0):
                raise AW('NO_VALID_BID result contains a winner')
            return
        if r['winner_bid_id']not in x or r['winner_bid_id']in disqualified:
            raise AW('result winner is not a valid bid')
        scores=r['scores']
        if not isinstance(scores,list)or len(scores)!=len(x):
            raise AW('result scores do not cover valid bids')
        score_map={}
        weights=AU(t.rubric)
        for q in scores:
            w=('bid_id','capability','delivery','price','support','technical','total')
            if not isinstance(q,dict)or tuple(sorted(q))!=w:
                raise AW('malformed score')
            if q['bid_id']not in x or q['bid_id']in score_map:
                raise AW('score bid is invalid')
            for h,limit in zip(('technical','delivery','price','capability','support'),weights):
                v=q[h]
                if not isinstance(v,int)or v<0 or v>limit:
                    raise AW('score exceeds rubric bound')
            total=sum((q[h]for h in('technical','delivery','price','capability','support')))
            if q['total']!=total:
                raise AW('score arithmetic mismatch')
            score_map[q['bid_id']]=q
        if set(score_map)!=set(x):
            raise AW('score coverage mismatch')
        o=sorted(score_map.values(),key=lambda row:(-row['total'],row['bid_id']))
        if o[0]['bid_id']!=r['winner_bid_id']or o[0]['total']!=r['winner_total_score']:
            raise AW('winner score mismatch')
        if len(o)>1:
            if o[0]['total']<=o[1]['total']:
                raise AW('unresolved score tie')
            if r['runner_up_bid_id']!=o[1]['bid_id']or r['runner_up_score']!=o[1]['total']:
                raise AW('runner-up mismatch')
        elif r['runner_up_bid_id']!='' or r['runner_up_score']!=0:
            raise AW('single bid runner-up must be empty')
    @gl.public.view
    def get_production_ready(self)->bool:
        return self.evaluator_bound
    @gl.public.view
    def get_evaluator_binding(self)->str:
        return AT({'bound':self.evaluator_bound,'address':str(self.evaluator_address),'version':self.evaluator_version,'evaluator_code_hash':self.evaluator_code_hash})
    @gl.public.view
    def get_contract_balance(self)->u256:
        return self.balance
    @gl.public.view
    def get_settlement_accounting(self,tender_id:str)->str:
        t=self.j(tender_id)
        return AT({'escrow_deposited':int(t.escrow_deposited),'winner_payout_amount':int(t.winner_payout_amount),'buyer_refund_amount':int(t.buyer_refund_amount),'payout_pending':t.payout_pending,'refund_pending':t.refund_pending,'payout_confirmed':t.payout_confirmed,'refund_confirmed':t.refund_confirmed,'settlement_state':t.settlement_state,'financial_outflow_pending':self.financial_outflow_pending,'financial_outflow_tender_id':self.financial_outflow_tender_id,'financial_outflow_kind':self.financial_outflow_kind,'financial_outflow_amount':int(self.financial_outflow_amount),'financial_outflow_balance_before':int(self.financial_outflow_balance_before)})
    @gl.public.view
    def get_tender(self,tender_id:str)->CoreTender:
        return self.j(tender_id)
    @gl.public.view
    def get_bid(self,bid_id:str)->CoreBid:
        b=self.bids.get(bid_id)
        if b is None:
            raise AW('bid does not exist')
        return b
    @gl.public.view
    def get_challenge(self,challenge_id:str)->CoreChallenge:
        c=self.challenges.get(challenge_id)
        if c is None:
            raise AW('challenge does not exist')
        return c
    @gl.public.view
    def list_tender_ids(self)->DynArray[str]:
        return self.tender_ids
    @gl.public.view
    def get_evaluation_context(self,tender_id:str)->str:
        t=self.j(tender_id)
        return AT({'core_schema_version':AB,'tender_id':tender_id,'status':t.status,'evaluation_nonce':int(t.evaluation_nonce),'snapshot_digest':t.closed_snapshot_digest,'evaluation_evaluator':str(self.evaluator_address),'evaluation_timeout_at':int(t.evaluation_timeout_at)})
    @gl.public.view
    def get_closed_snapshot(self,tender_id:str)->str:
        t=self.j(tender_id)
        if t.status not in(C,D,E,F,G,H,I,J,K,L,M,N,P):
            raise AW('closed snapshot is unavailable')
        return self.o(tender_id)
    @gl.public.view
    def get_review_context(self,tender_id:str,review_nonce:u64)->str:
        t=self.j(tender_id)
        if t.review_nonce!=review_nonce or t.status!=I:
            raise AW('review context is stale')
        y=[]
        for challenge_id in sorted(self.challenge_ids):
            c=self.challenges[challenge_id]
            if c.tender_id==tender_id and c.status==V:
                y.append({'challenge_id':c.challenge_id,'tender_id':c.tender_id,'challenger':str(c.challenger),'reason_code':c.reason_code,'target_bid_id':c.target_bid_id,'referenced_evidence_id':c.referenced_evidence_id,'challenge_url':c.challenge_url,'challenge_sha256':c.challenge_sha256,'claims':''})
        return AT({'tender_id':tender_id,'status':t.status,'evaluation_nonce':int(t.evaluation_nonce),'review_nonce':int(review_nonce),'snapshot_digest':t.closed_snapshot_digest,'original_result_digest':t.evaluation_result_digest,'challenge_set_digest':t.challenge_set_digest,'review_evaluator':str(self.evaluator_address),'review_timeout_at':int(t.review_timeout_at),'challenges':y})
    @gl.public.write
    def bind_evaluator(self,evaluator_address:Address,evaluator_version:str,evaluator_code_hash:str):
        if self.evaluator_bound:
            raise AW('evaluator is already permanently bound')
        if gl.message.sender_address!=self.bootstrapper:
            raise AW('only the deployment bootstrapper may bind evaluator')
        if evaluator_address==AQ:
            raise AW('evaluator address is zero')
        if evaluator_version!=AC:
            raise AW('unsupported evaluator version')
        if not AS(evaluator_code_hash):
            raise AW('invalid evaluator code hash')
        self.evaluator_address=evaluator_address
        self.evaluator_version=evaluator_version
        self.evaluator_code_hash=evaluator_code_hash
        self.evaluator_bound=True
    @gl.public.write.payable
    def create_tender(self,tender_id:str,title:str,brief_url:str,brief_sha256:str,max_budget_wei:u256,max_delivery_days:u64,min_support_days:u64,bidding_deadline:u64,response_window_seconds:u64,requirements:str,technical_weight:u8,delivery_weight:u8,price_weight:u8,capability_weight:u8,support_weight:u8,evidence_policy:str):
        self.b(tender_id,AJ,'tender_id')
        self.b(title,AK,'title')
        self.c(brief_url,'brief_url')
        if not AS(brief_sha256):
            raise AW('invalid brief hash')
        self.b(requirements,AM,'requirements')
        self.b(evidence_policy,AM,'evidence policy')
        if tender_id in self.tenders:
            raise AW('tender already exists')
        if max_budget_wei==u256(0):
            raise AW('invalid maximum budget')
        if max_delivery_days==u64(0)or min_support_days==u64(0):
            raise AW('invalid delivery or support constraint')
        if bidding_deadline<=self.a():
            raise AW('bidding deadline must be in the future')
        if response_window_seconds<AE:
            raise AW('response window below protocol minimum')
        rubric='technical='+str(technical_weight)+';delivery='+str(delivery_weight)+';price='+str(price_weight)+';capability='+str(capability_weight)+';support='+str(support_weight)
        try:
            AU(rubric)
        except Exception:
            raise AW('rubric must total exactly 100')
        self.f()
        if gl.message.value!=max_budget_wei:
            raise AW('exact maximum-budget funding is required')
        self.tenders[tender_id]=CoreTender(tender_id,gl.message.sender_address,title,brief_url,brief_sha256,max_budget_wei,max_delivery_days,min_support_days,bidding_deadline,response_window_seconds,A,requirements,rubric,evidence_policy,gl.message.value,'',u64(0),u64(0),'','','',u64(0),u64(0),u64(0),u64(0),'',Q,u256(0),u256(0),False,False,False,False,'')
        self.tender_ids.append(tender_id)
        self.total_locked_escrow=self.total_locked_escrow+gl.message.value
    @gl.public.write
    def open_tender(self,tender_id:str):
        self.e()
        t=self.j(tender_id)
        self.d(t)
        if t.status!=A:
            raise AW('only draft tenders may open')
        if self.balance<self.total_locked_escrow or self.a()>=t.bidding_deadline:
            raise AW('escrow or deadline is invalid')
        t.status=B
        self.tenders[tender_id]=t
    @gl.public.write
    def submit_bid(self,bid_id:str,tender_id:str,price_wei:u256,delivery_days:u64,support_days:u64,proposal_url:str,proposal_sha256:str,evidence_commitments:str,schema_version:str='tendercouncil.bid.v1'):
        self.e()
        self.b(bid_id,AJ,'bid_id')
        self.c(proposal_url,'proposal_url')
        if not AS(proposal_sha256)or not AV(evidence_commitments):
            raise AW('invalid proposal or evidence commitment')
        if schema_version!='tendercouncil.bid.v1':
            raise AW('unsupported bid schema')
        if bid_id in self.bids:
            raise AW('bid already exists')
        t=self.j(tender_id)
        if t.status!=B or self.a()>t.bidding_deadline:
            raise AW('bidding is closed')
        if price_wei==u256(0):
            raise AW('price_wei must be positive')
        for known_id in self.bid_ids:
            known=self.bids[known_id]
            if known.tender_id==tender_id and known.bidder==gl.message.sender_address:
                raise AW('one immutable bid per wallet is required')
        self.bids[bid_id]=CoreBid(bid_id,tender_id,gl.message.sender_address,price_wei,delivery_days,support_days,proposal_url,proposal_sha256,evidence_commitments,schema_version,self.a())
        self.bid_ids.append(bid_id)
    @gl.public.write
    def close_tender(self,tender_id:str):
        t=self.j(tender_id)
        self.d(t)
        if t.status!=B or self.a()<t.bidding_deadline:
            raise AW('tender cannot close yet')
        snapshot=self.o(tender_id)
        t.closed_snapshot_digest=AR(snapshot)
        t.status=C
        self.tenders[tender_id]=t
    @gl.public.write
    def start_evaluation(self,tender_id:str):
        self.e()
        t=self.j(tender_id)
        self.d(t)
        if t.status!=C:
            raise AW('only closed tenders may be evaluated')
        self.k(t)
    @gl.public.write
    def expire_evaluation_attempt(self,tender_id:str):
        t=self.j(tender_id)
        if t.status!=D:
            raise AW('evaluation is not awaiting a callback')
        if self.a()<=t.evaluation_timeout_at:
            raise AW('evaluation attempt timeout has not elapsed')
        self.l(t)
        self.tenders[tender_id]=t
    @gl.public.write
    def retry_evaluation(self,tender_id:str):
        self.e()
        t=self.j(tender_id)
        if t.status!=E:
            raise AW('evaluation is not retryable')
        if AR(self.o(tender_id))!=t.closed_snapshot_digest:
            raise AW('closed snapshot changed before retry')
        self.k(t)
    @gl.public.write
    def receive_evaluation_result(self,tender_id:str,nonce:u64,snapshot_digest:str,evaluator_schema_version:str,result_type:str,winner_bid_id:str,result_digest:str):
        if gl.message.sender_address!=self.evaluator_address:
            raise AW('caller is not the bound evaluator')
        t=self.j(tender_id)
        if t.status!=D or t.evaluation_nonce!=nonce:
            raise AW('evaluation callback is stale or out of state')
        if snapshot_digest!=t.closed_snapshot_digest:
            raise AW('evaluation snapshot mismatch')
        if evaluator_schema_version!=AC:
            raise AW('evaluator schema mismatch')
        if result_type not in('COMPARATIVE','NO_VALID_BID'):
            raise AW('unknown result type')
        p=AX(self.evaluator_address).view().get_evaluation_result(tender_id,nonce)
        if AR(p)!=result_digest:
            raise AW('evaluation result digest mismatch')
        r=json.loads(p)
        if r.get('winner_bid_id','')!=winner_bid_id:
            raise AW('callback winner mismatch')
        self.q(t,r,result_type)
        t.evaluation_result_digest=result_digest
        if result_type=='NO_VALID_BID':
            t.status=N
            t.settlement_state=R
        else:
            t.provisional_winner=winner_bid_id
            t.response_window_start=u64(0)
            t.response_window_end=u64(0)
            t.status=G
        self.tenders[tender_id]=t
    @gl.public.write
    def receive_evaluation_failure(self,tender_id:str,nonce:u64,snapshot_digest:str,failure_code:str,failure_digest:str):
        if gl.message.sender_address!=self.evaluator_address:
            raise AW('caller is not the bound evaluator')
        t=self.j(tender_id)
        if t.status!=D or t.evaluation_nonce!=nonce:
            raise AW('evaluation failure callback is stale')
        if snapshot_digest!=t.closed_snapshot_digest or failure_code not in('MODEL_CANDIDATE_INVALID','MODEL_PROVIDER_UNAVAILABLE'):
            raise AW('evaluation failure correlation failed')
        p=AX(self.evaluator_address).view().get_evaluation_result(tender_id,nonce)
        if AR(p)!=failure_digest:
            raise AW('evaluation failure digest mismatch')
        f=json.loads(p)
        if not isinstance(f,dict)or len(f)!=2 or f.get('state')!=failure_code or(f.get('result')!={}):
            raise AW('malformed evaluation failure')
        self.l(t)
        self.tenders[tender_id]=t
    @gl.public.write
    def start_response_window(self,tender_id:str):
        t=self.j(tender_id)
        if t.status!=G:
            raise AW('no provisional award exists')
        t.response_window_start=self.a()
        t.response_window_end=t.response_window_start+t.response_window_seconds
        t.status=H
        self.tenders[tender_id]=t
    @gl.public.write
    def submit_challenge(self,challenge_id:str,tender_id:str,reason_code:str,target_bid_id:str,referenced_evidence_id:str,challenge_url:str,challenge_sha256:str):
        self.b(challenge_id,AJ,'challenge_id')
        t=self.j(tender_id)
        if t.status!=H or self.a()>t.response_window_end:
            raise AW('response window is closed')
        if reason_code not in AA or challenge_id in self.challenges:
            raise AW('invalid or duplicate challenge')
        target=self.bids.get(target_bid_id)
        if target is None or target.tender_id!=tender_id:
            raise AW('invalid challenge target')
        bidder=False
        for bid_id in self.bid_ids:
            b=self.bids[bid_id]
            if b.tender_id==tender_id and b.bidder==gl.message.sender_address:
                bidder=True
        if not bidder:
            raise AW('only a tender bidder may challenge')
        if reason_code in(X,Z):
            if referenced_evidence_id=='' or referenced_evidence_id+'|' not in target.evidence_commitments:
                raise AW('challenge evidence was not committed before close')
        elif referenced_evidence_id!='':
            raise AW('evidence reference is not allowed for this reason')
        if(challenge_url=='')!=(challenge_sha256==''):
            raise AW('challenge URL and hash must be paired')
        if challenge_url!='':
            self.c(challenge_url,'challenge_url')
            if not AS(challenge_sha256):
                raise AW('invalid challenge hash')
        for old_id in self.challenge_ids:
            old=self.challenges[old_id]
            if old.tender_id==tender_id and old.challenger==gl.message.sender_address:
                raise AW('one challenge per bidder is required')
        count=sum((1 for old_id in self.challenge_ids if self.challenges[old_id].tender_id==tender_id))
        if count>=AO:
            raise AW('challenge limit exceeded')
        self.challenges[challenge_id]=CoreChallenge(challenge_id,tender_id,gl.message.sender_address,reason_code,target_bid_id,referenced_evidence_id,challenge_url,challenge_sha256,self.a(),V,'')
        self.challenge_ids.append(challenge_id)
    @gl.public.write
    def advance_after_response(self,tender_id:str):
        t=self.j(tender_id)
        if t.status!=H or self.a()<=t.response_window_end:
            raise AW('response window is still open')
        admitted=0
        for challenge_id in self.challenge_ids:
            c=self.challenges[challenge_id]
            if c.tender_id!=tender_id:
                continue
            if c.status==V:
                admitted+=1
        if admitted==0:
            t.final_winner=t.provisional_winner
            t.status=K
            t.settlement_state=R
        else:
            t.challenge_set_digest=self.p(tender_id)
            self.m(t)
            return
        self.tenders[tender_id]=t
    @gl.public.write
    def receive_review_result(self,tender_id:str,evaluation_nonce:u64,review_nonce:u64,snapshot_digest:str,original_result_digest:str,challenge_set_digest:str,decision:str,winner_bid_id:str,result_digest:str):
        if gl.message.sender_address!=self.evaluator_address:
            raise AW('caller is not the bound evaluator')
        t=self.j(tender_id)
        if t.status!=I or t.evaluation_nonce!=evaluation_nonce or t.review_nonce!=review_nonce:
            raise AW('review callback is stale')
        if snapshot_digest!=t.closed_snapshot_digest or original_result_digest!=t.evaluation_result_digest or challenge_set_digest!=t.challenge_set_digest:
            raise AW('review correlation digest mismatch')
        p=AX(self.evaluator_address).view().get_review_result(tender_id,review_nonce)
        if AR(p)!=result_digest:
            raise AW('review result digest mismatch')
        r=json.loads(p)
        if r.get('decision')!=decision or r.get('winner_bid_id')!=winner_bid_id:
            raise AW('review callback payload mismatch')
        if decision=='NO_VALID_BID':
            t.status=N
            t.final_winner=''
            t.settlement_state=R
        elif decision in('UPHOLD','REPLACE_WINNER'):
            if winner_bid_id=='' or winner_bid_id not in[bid_id for bid_id in self.bid_ids if self.bids[bid_id].tender_id==tender_id]:
                raise AW('review winner is not a tender bid')
            original_payload=AX(self.evaluator_address).view().get_evaluation_result(tender_id,evaluation_nonce)
            original=json.loads(original_payload)
            if winner_bid_id not in original.get('valid_bid_ids',[]):
                raise AW('review winner was not an original valid bid')
            t.final_winner=winner_bid_id
            t.status=K
            t.settlement_state=R
        else:
            raise AW('invalid review decision')
        self.tenders[tender_id]=t
    @gl.public.write
    def receive_review_failure(self,tender_id:str,evaluation_nonce:u64,review_nonce:u64,snapshot_digest:str,original_result_digest:str,challenge_set_digest:str,failure_code:str,failure_digest:str):
        if gl.message.sender_address!=self.evaluator_address:
            raise AW('caller is not the bound evaluator')
        t=self.j(tender_id)
        if t.status!=I or t.evaluation_nonce!=evaluation_nonce or t.review_nonce!=review_nonce:
            raise AW('review failure callback is stale')
        if snapshot_digest!=t.closed_snapshot_digest or original_result_digest!=t.evaluation_result_digest or challenge_set_digest!=t.challenge_set_digest or(failure_code not in('MODEL_CANDIDATE_INVALID','MODEL_PROVIDER_UNAVAILABLE')):
            raise AW('review failure correlation failed')
        p=AX(self.evaluator_address).view().get_review_result(tender_id,review_nonce)
        if AR(p)!=failure_digest:
            raise AW('review failure digest mismatch')
        f=json.loads(p)
        if not isinstance(f,dict)or len(f)!=2 or f.get('state')!=failure_code or(f.get('result')!={}):
            raise AW('malformed review failure')
        self.n(t)
        self.tenders[tender_id]=t
    @gl.public.write
    def expire_review_attempt(self,tender_id:str):
        t=self.j(tender_id)
        if t.status!=I:
            raise AW('review is not awaiting a callback')
        if self.a()<=t.review_timeout_at:
            raise AW('review attempt timeout has not elapsed')
        self.n(t)
        self.tenders[tender_id]=t
    @gl.public.write
    def retry_review(self,tender_id:str):
        self.e()
        t=self.j(tender_id)
        if t.status!=J:
            raise AW('review is not retryable')
        if AR(self.o(tender_id))!=t.closed_snapshot_digest or self.p(tender_id)!=t.challenge_set_digest:
            raise AW('immutable review inputs changed before retry')
        self.m(t)
    @gl.public.write
    def settle_award(self,tender_id:str):
        t=self.j(tender_id)
        if t.status!=K or t.settlement_state!=R:
            raise AW('only an unsettled awarded tender may settle')
        self.f()
        winner=self.bids.get(t.final_winner)
        if winner is None or winner.tender_id!=tender_id:
            raise AW('final winner is invalid')
        m=winner.price_wei
        if m==u256(0)or m>t.escrow_deposited:
            raise AW('winner payout exceeds escrow')
        t.winner_payout_amount=m
        t.buyer_refund_amount=t.escrow_deposited-m
        if t.escrow_deposited!=t.winner_payout_amount+t.buyer_refund_amount:
            raise AW('settlement accounting invariant failed')
        t.payout_pending=True
        self.g(tender_id,'PAYOUT',m)
        AY(winner.bidder).emit_transfer(value=m,on='finalized')
        t.settlement_state=S
        t.status=L
        self.tenders[tender_id]=t
    @gl.public.write
    def confirm_settlement(self,tender_id:str):
        t=self.j(tender_id)
        if t.status!=L or t.settlement_state!=S:
            raise AW('settlement is not pending')
        if not self.financial_outflow_pending or self.financial_outflow_tender_id!=tender_id or self.financial_outflow_kind!='PAYOUT':
            raise AW('payout outflow correlation failed')
        if self.balance!=self.financial_outflow_balance_before-self.financial_outflow_amount:
            raise AW('finalized transfer was not verified')
        t.payout_pending=False
        t.payout_confirmed=True
        self.h()
        if t.buyer_refund_amount>u256(0):
            t.refund_pending=True
            t.refund_kind='REFUND'
            self.g(tender_id,'REFUND',t.buyer_refund_amount)
            AY(t.buyer).emit_transfer(value=t.buyer_refund_amount,on='finalized')
            t.settlement_state=U
        else:
            t.refund_pending=False
            t.refund_confirmed=True
            self.total_locked_escrow=self.total_locked_escrow-t.escrow_deposited
            t.settlement_state=T
            t.status=M
        self.tenders[tender_id]=t
    @gl.public.write
    def cancel_tender(self,tender_id:str):
        t=self.j(tender_id)
        self.d(t)
        if t.status!=A:
            raise AW('only an unopened tender may be cancelled')
        self.f()
        t.winner_payout_amount=u256(0)
        t.buyer_refund_amount=t.escrow_deposited
        t.refund_pending=True
        t.refund_kind='CANCEL_REFUND'
        self.g(tender_id,'CANCEL_REFUND',t.escrow_deposited)
        AY(t.buyer).emit_transfer(value=t.escrow_deposited,on='finalized')
        t.status=P
        t.settlement_state=U
        self.tenders[tender_id]=t
    @gl.public.write
    def confirm_refund(self,tender_id:str):
        t=self.j(tender_id)
        if t.status not in(P,L)or t.settlement_state!=U:
            raise AW('refund is not pending')
        if not self.financial_outflow_pending or self.financial_outflow_tender_id!=tender_id or self.financial_outflow_kind not in('CANCEL_REFUND','NO_VALID_REFUND','REFUND','EVALUATION_FAILED_REFUND'):
            raise AW('refund outflow correlation failed')
        if self.balance!=self.financial_outflow_balance_before-self.financial_outflow_amount:
            raise AW('refund transfer was not verified')
        t.refund_pending=False
        t.refund_confirmed=True
        self.h()
        self.total_locked_escrow=self.total_locked_escrow-t.escrow_deposited
        if t.winner_payout_amount==u256(0)and t.status==P:
            if t.settlement_state==U and t.buyer_refund_amount==t.escrow_deposited:
                if t.refund_kind=='CANCEL_REFUND':
                    t.status=O
                elif t.refund_kind=='EVALUATION_FAILED_REFUND':
                    t.status=F
                else:
                    t.status=N
        elif t.winner_payout_amount>u256(0)and t.status==L and(t.refund_kind=='REFUND')and t.payout_confirmed and(t.escrow_deposited==t.winner_payout_amount+t.buyer_refund_amount):
            t.status=M
        t.settlement_state=T
        self.tenders[tender_id]=t
    @gl.public.write
    def refund_no_valid_bid(self,tender_id:str):
        t=self.j(tender_id)
        self.d(t)
        if t.status!=N or t.settlement_state!=R:
            raise AW('tender is not refundable')
        self.f()
        t.winner_payout_amount=u256(0)
        t.buyer_refund_amount=t.escrow_deposited
        t.refund_pending=True
        t.refund_kind='NO_VALID_REFUND'
        self.g(tender_id,'NO_VALID_REFUND',t.escrow_deposited)
        AY(t.buyer).emit_transfer(value=t.escrow_deposited,on='finalized')
        t.status=P
        t.settlement_state=U
        self.tenders[tender_id]=t
    @gl.public.write
    def confirm_no_valid_refund(self,tender_id:str):
        self.confirm_refund(tender_id)
    @gl.public.write
    def refund_failed_evaluation(self,tender_id:str):
        t=self.j(tender_id)
        if t.status!=F or int(t.evaluation_nonce)<AG:
            raise AW('bounded evaluation failure is not established')
        self.i(t,'EVALUATION_FAILED_REFUND')
def AW(message:str):
    return gl.vm.UserError(message)
