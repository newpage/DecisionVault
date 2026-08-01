"use client";
import {useEffect,useState} from "react";
import {AlertTriangle,Building2,CheckCircle2,Cpu,Plus,ShieldCheck} from "lucide-react";
import Shell from "@/components/Shell";
import {Card,PageHeader} from "@/components/Page";
import {api} from "@/lib/api";

type Workspace={id:string;name:string};
type Concept={id:string;name:string;slug:string};
type Decision={id:string;title:string;question:string;status:string;recommendation:string;supplier_name:string;supplier_category:string;supplier_location:string;owner_name:string;due_date:string|null;priority:string;risk_level:string;readiness_score:number;readiness_status:string;evidence_summary:{missing_information?:string[]}};

const defaults={title:"Qualify electronic manufacturing supplier",question:"Should this electronic manufacturer be approved to supply production components?",supplier_name:"Apex Circuit Manufacturing",supplier_category:"Electronic Manufacturer",supplier_location:"San Jose, California",owner_name:"Supplier Quality Manager",due_date:"",priority:"high",risk_level:"high",decision_type:"initial_qualification",business_unit:"Electronics Supply Chain"};

export default function Decisions(){
 const [items,setItems]=useState<Decision[]>([]),[workspaces,setWorkspaces]=useState<Workspace[]>([]),[concepts,setConcepts]=useState<Concept[]>([]);
 const [workspaceId,setWorkspaceId]=useState(""),[conceptId,setConceptId]=useState(""),[form,setForm]=useState(defaults),[show,setShow]=useState(false),[error,setError]=useState("");
 async function load(){const[d,w,c]=await Promise.all([api<Decision[]>("/decisions"),api<Workspace[]>("/workspaces"),api<Concept[]>("/business-concepts")]);setItems(d);setWorkspaces(w);setConcepts(c);if(!workspaceId&&w[0])setWorkspaceId(w[0].id);if(!conceptId){const s=c.find(x=>x.slug==="supplier-qualification");if(s)setConceptId(s.id)}}
 useEffect(()=>{void load().catch(e=>setError(e instanceof Error?e.message:"Unable to load"))},[]);
 function update(name:string,value:string){setForm(v=>({...v,[name]:value}))}
 async function create(){setError("");try{await api("/decisions",{method:"POST",body:JSON.stringify({workspace_id:workspaceId,business_concept_id:conceptId||null,...form,due_date:form.due_date||null})});setShow(false);setForm(defaults);await load()}catch(e){setError(e instanceof Error?e.message:"Unable to create decision")}}
 return <Shell>
  <PageHeader eyebrow="Supplier Decision Intelligence" title="Electronic Manufacturer Decisions" description="Qualify electronics suppliers using transparent evidence, risk, ownership, and accountable review." action={<button className="btn primary row" onClick={()=>setShow(v=>!v)}><Plus size={16}/>New supplier decision</button>}/>
  <div className="decision-summary-grid">
   <Card className="metric"><span className="muted">Open decisions</span><strong>{items.filter(x=>!["approved","closed"].includes(x.status)).length}</strong></Card>
   <Card className="metric"><span className="muted">High-risk reviews</span><strong>{items.filter(x=>["high","critical"].includes(x.risk_level)).length}</strong></Card>
   <Card className="metric"><span className="muted">Ready for review</span><strong>{items.filter(x=>x.readiness_score>=80).length}</strong></Card>
  </div>
  {show?<Card className="decision-form">
   <div className="section-title"><Cpu size={19}/><h2>New Electronic Manufacturer Qualification</h2></div>
   <div className="decision-form-grid">
    {([["supplier_name","Supplier name"],["supplier_location","Supplier location"],["owner_name","Decision owner"],["due_date","Due date"]] as const).map(([k,l])=><label key={k}><span>{l}</span><input type={k==="due_date"?"date":"text"} className="input" value={form[k]} onChange={e=>update(k,e.target.value)}/></label>)}
    <label><span>Priority</span><select className="input" value={form.priority} onChange={e=>update("priority",e.target.value)}>{["low","medium","high","critical"].map(x=><option key={x}>{x}</option>)}</select></label>
    <label><span>Risk level</span><select className="input" value={form.risk_level} onChange={e=>update("risk_level",e.target.value)}>{["low","medium","high","critical"].map(x=><option key={x}>{x}</option>)}</select></label>
    <label><span>Workspace</span><select className="input" value={workspaceId} onChange={e=>setWorkspaceId(e.target.value)}>{workspaces.map(x=><option value={x.id} key={x.id}>{x.name}</option>)}</select></label>
    <label><span>Business concept</span><select className="input" value={conceptId} onChange={e=>setConceptId(e.target.value)}>{concepts.map(x=><option value={x.id} key={x.id}>{x.name}</option>)}</select></label>
   </div>
   <label><span>Decision title</span><input className="input" value={form.title} onChange={e=>update("title",e.target.value)}/></label>
   <label><span>Decision question</span><textarea className="input textarea" value={form.question} onChange={e=>update("question",e.target.value)}/></label>
   <div className="decision-control-note"><ShieldCheck size={18}/>Evidence is assessed across quality certification, manufacturing controls, traceability, counterfeit prevention, supply continuity, and cybersecurity.</div>
   <button className="btn primary" onClick={()=>void create()}>Create qualification decision</button>
  </Card>:null}
  {error?<Card className="danger">{error}</Card>:null}
  <div className="decision-list">{items.map(d=>{const missing=d.evidence_summary?.missing_information??[];return <Card className="supplier-decision-card" key={d.id}>
   <div className="row between decision-card-header"><div className="row"><div className="supplier-icon"><Building2 size={21}/></div><div><div className="eyebrow">{d.supplier_category}</div><h2>{d.supplier_name||d.title}</h2><div className="muted">{d.title}</div></div></div><div className={`readiness readiness-${d.readiness_status}`}><strong>{d.readiness_score}%</strong><span>Decision readiness</span></div></div>
   <div className="decision-meta-grid"><span><b>Owner</b>{d.owner_name||"Unassigned"}</span><span><b>Status</b>{d.status.replaceAll("_"," ")}</span><span><b>Priority</b>{d.priority}</span><span><b>Risk</b>{d.risk_level}</span><span><b>Location</b>{d.supplier_location||"Not provided"}</span><span><b>Due</b>{d.due_date??"Not scheduled"}</span></div>
   <p className="decision-question">{d.question}</p><p className="muted">{d.recommendation}</p>
   {missing.length?<div className="decision-findings"><div className="row"><AlertTriangle size={17}/><strong>Information requiring attention</strong></div>{missing.map(x=><div key={x}>• {x}</div>)}</div>:<div className="decision-clear row"><CheckCircle2 size={17}/>Evidence baseline is complete for formal review.</div>}
  </Card>})}</div>
 </Shell>
}
