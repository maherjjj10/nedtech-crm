import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Checkbox } from "../components/ui/checkbox";
import { Badge } from "../components/ui/badge";
import { CheckCircle2, Download, XCircle, MessageSquare, PenLine, Type } from "lucide-react";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api/v1`;

function SignaturePad({ onChange, disabled }) {
  const canvasRef = useRef(null);
  const drawingRef = useRef(false);

  useEffect(() => {
    const c = canvasRef.current;
    if (!c) return;
    const ratio = window.devicePixelRatio || 1;
    c.width = c.offsetWidth * ratio;
    c.height = c.offsetHeight * ratio;
    const ctx = c.getContext("2d");
    ctx.scale(ratio, ratio);
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.strokeStyle = "#171717";
  }, []);

  const getPos = (evt) => {
    const c = canvasRef.current;
    const rect = c.getBoundingClientRect();
    const t = evt.touches?.[0];
    const clientX = t ? t.clientX : evt.clientX;
    const clientY = t ? t.clientY : evt.clientY;
    return { x: clientX - rect.left, y: clientY - rect.top };
  };
  const start = (e) => {
    if (disabled) return;
    e.preventDefault();
    drawingRef.current = true;
    const { x, y } = getPos(e);
    const ctx = canvasRef.current.getContext("2d");
    ctx.beginPath(); ctx.moveTo(x, y);
  };
  const draw = (e) => {
    if (!drawingRef.current) return;
    e.preventDefault();
    const { x, y } = getPos(e);
    const ctx = canvasRef.current.getContext("2d");
    ctx.lineTo(x, y); ctx.stroke();
  };
  const end = () => {
    if (!drawingRef.current) return;
    drawingRef.current = false;
    onChange?.(canvasRef.current.toDataURL("image/png"));
  };
  const clear = () => {
    const c = canvasRef.current;
    const ctx = c.getContext("2d");
    ctx.clearRect(0, 0, c.width, c.height);
    onChange?.(null);
  };

  return (
    <div>
      <canvas
        ref={canvasRef}
        onMouseDown={start} onMouseMove={draw} onMouseUp={end} onMouseLeave={end}
        onTouchStart={start} onTouchMove={draw} onTouchEnd={end}
        className="w-full h-40 border border-border/60 rounded-md bg-white touch-none"
        data-testid="signature-canvas"
      />
      <div className="flex justify-end mt-1">
        <Button type="button" variant="ghost" size="sm" onClick={clear} data-testid="signature-clear">Clear</Button>
      </div>
    </div>
  );
}

export default function PublicContract() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ signer_name: "", signer_email: "", consent: false, signature_type: "typed", signature_data: null });
  const [saving, setSaving] = useState(false);
  const [signed, setSigned] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [comment, setComment] = useState("");
  const [comments, setComments] = useState([]);

  const refresh = () => {
    axios.get(`${API}/public/contracts/${token}`)
      .then(r => {
        setData(r.data);
        setComments(r.data.contract.comments || []);
        if (["signed", "completed"].includes(r.data.contract.status)) setSigned(true);
      })
      .catch(e => setError(e?.response?.data?.detail || "Contract not found"));
  };
  useEffect(refresh, [token]);

  const submitSign = async (e) => {
    e.preventDefault();
    if (!form.consent) { toast.error("Please confirm consent"); return; }
    if (form.signature_type === "drawn" && !form.signature_data) { toast.error("Please draw your signature"); return; }
    setSaving(true);
    try {
      await axios.post(`${API}/public/contracts/${token}/sign`, form);
      setSigned(true);
      toast.success("Signed — thank you");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed");
    } finally { setSaving(false); }
  };

  const submitReject = async () => {
    if (!rejectReason.trim()) { toast.error("Please share a reason"); return; }
    try {
      await axios.post(`${API}/public/contracts/${token}/reject`, { signer_name: form.signer_name || "client", reason: rejectReason });
      toast.success("Contract rejected");
      setRejecting(false);
      refresh();
    } catch (err) { toast.error(err?.response?.data?.detail || "Failed"); }
  };

  const submitComment = async (e) => {
    e.preventDefault();
    if (!comment.trim() || !form.signer_name.trim()) { toast.error("Enter your name and a comment"); return; }
    try {
      const r = await axios.post(`${API}/public/contracts/${token}/comment`, { author: form.signer_name, body: comment });
      setComments(cs => [...cs, r.data]);
      setComment("");
    } catch { toast.error("Failed"); }
  };

  const downloadPdf = () => {
    window.location.href = `${API}/public/contracts/${token}/pdf`;
  };

  if (error) return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <Card className="p-8 max-w-md text-center border-border/70">
        <h1 className="text-xl font-bold">Contract unavailable</h1>
        <p className="text-sm text-muted-foreground mt-2">{error}</p>
      </Card>
    </div>
  );
  if (!data) return <div className="min-h-screen flex items-center justify-center text-sm text-muted-foreground">Loading…</div>;
  const c = data.contract; const t = data.tenant;
  const expired = c.status === "expired";
  const cancelled = c.status === "cancelled";

  return (
    <div className="min-h-screen bg-background text-foreground py-6 sm:py-10 px-4">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Contract from</div>
            <div className="text-2xl font-bold tracking-tight">{t.name}</div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={signed ? "default" : "outline"} data-testid="contract-status-badge">{c.status}</Badge>
            <Button variant="outline" size="sm" onClick={downloadPdf} data-testid="pub-download-pdf"><Download className="h-4 w-4 mr-1" />PDF</Button>
          </div>
        </div>

        <Card className="p-6 sm:p-8 border-border/70">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight" data-testid="contract-title">{c.title}</h1>
          <div className="text-xs text-muted-foreground mt-1">
            Verification ID: <span className="font-mono">{c.verification_id}</span>
            {c.client_snapshot?.company && <> · Prepared for {c.client_snapshot.company}</>}
          </div>
          <div className="mt-6 contract-html text-[14.5px]" dangerouslySetInnerHTML={{ __html: c.rendered_html || c.body_html }} />

          {c.signature && (
            <div className="mt-8 border-t border-border pt-4">
              <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">Signed by</div>
              {c.signature.signature_type === "drawn" && c.signature.signature_data
                ? <img src={c.signature.signature_data} alt="Signature" className="h-16 object-contain" />
                : <div className="font-serif italic text-2xl">{c.signature.signer_name}</div>}
              <div className="text-xs text-muted-foreground mt-1">{c.signature.signer_name} · {new Date(c.signature.signed_at).toLocaleString()} · IP {c.signature.ip}</div>
            </div>
          )}
        </Card>

        {!signed && !expired && !cancelled && (
          <Card className="p-6 border-border/70">
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-4">Sign this contract</div>
            <form onSubmit={submitSign} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5 col-span-2 sm:col-span-1"><Label>Full legal name</Label><Input value={form.signer_name} onChange={(e)=>setForm({...form, signer_name:e.target.value})} required data-testid="contract-signer-input" /></div>
                <div className="space-y-1.5 col-span-2 sm:col-span-1"><Label>Email (optional)</Label><Input type="email" value={form.signer_email} onChange={(e)=>setForm({...form, signer_email:e.target.value})} data-testid="contract-signer-email" /></div>
              </div>

              <div>
                <Label className="text-xs uppercase tracking-widest text-muted-foreground">Signature method</Label>
                <div className="mt-2 flex gap-2">
                  <button type="button" onClick={()=>setForm({...form, signature_type:"typed", signature_data:null})}
                          className={`flex-1 border rounded-md py-2 text-sm flex items-center justify-center gap-2 ${form.signature_type==="typed" ? "border-foreground bg-accent" : "border-border/60"}`}
                          data-testid="sig-type-typed"><Type className="h-4 w-4" />Type</button>
                  <button type="button" onClick={()=>setForm({...form, signature_type:"drawn"})}
                          className={`flex-1 border rounded-md py-2 text-sm flex items-center justify-center gap-2 ${form.signature_type==="drawn" ? "border-foreground bg-accent" : "border-border/60"}`}
                          data-testid="sig-type-drawn"><PenLine className="h-4 w-4" />Draw (mouse / touch)</button>
                </div>
              </div>

              {form.signature_type === "typed" && form.signer_name && (
                <div className="border border-border/60 rounded-md p-4 bg-white">
                  <div className="font-serif italic text-3xl text-foreground">{form.signer_name}</div>
                </div>
              )}
              {form.signature_type === "drawn" && (
                <SignaturePad onChange={(d)=>setForm({...form, signature_data:d})} />
              )}

              <label className="flex items-start gap-2 text-sm">
                <Checkbox checked={form.consent} onCheckedChange={(v)=>setForm({...form, consent: !!v})} data-testid="contract-consent" className="mt-0.5" />
                <span>I agree that {form.signature_type === "typed" ? "typing my name" : "drawing my signature"} and clicking Sign constitutes my legal signature and I intend to be bound by this contract.</span>
              </label>

              <div className="flex flex-col sm:flex-row gap-2 pt-2">
                <Button type="submit" disabled={saving} className="flex-1" data-testid="contract-sign-btn">
                  <CheckCircle2 className="h-4 w-4 mr-1" />{saving ? "Signing…" : "Sign contract"}
                </Button>
                <Button type="button" variant="outline" onClick={()=>setRejecting(true)} className="sm:w-40" data-testid="contract-reject-open"><XCircle className="h-4 w-4 mr-1" />Reject</Button>
              </div>
            </form>
          </Card>
        )}

        {rejecting && (
          <Card className="p-6 border-border/70">
            <div className="text-sm font-semibold mb-2">Reject this contract</div>
            <Textarea rows={4} placeholder="Share a reason (required)" value={rejectReason} onChange={(e)=>setRejectReason(e.target.value)} data-testid="reject-reason" />
            <div className="flex gap-2 mt-3">
              <Button variant="destructive" onClick={submitReject} data-testid="reject-submit">Reject contract</Button>
              <Button variant="ghost" onClick={()=>setRejecting(false)}>Cancel</Button>
            </div>
          </Card>
        )}

        {signed && (
          <Card className="p-6 border-border/70 bg-accent">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-6 w-6" />
              <div>
                <div className="font-semibold">Signed — thank you.</div>
                <div className="text-xs text-muted-foreground">A copy has been recorded and shared with {t.name}. You can also download the PDF above.</div>
              </div>
            </div>
          </Card>
        )}

        {(expired || cancelled) && !signed && (
          <Card className="p-6 border-border/70 bg-muted/40">
            <div className="text-sm">This contract is {c.status} and can no longer be signed. Please contact {t.name} for a new copy.</div>
          </Card>
        )}

        <Card className="p-6 border-border/70">
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-3 flex items-center gap-1"><MessageSquare className="h-3.5 w-3.5" />Comments</div>
          <div className="space-y-2 mb-3">
            {comments.length === 0 && <div className="text-xs text-muted-foreground">No comments yet.</div>}
            {comments.map(cm => (
              <div key={cm.id} className="border border-border/60 rounded-md p-3 text-sm">
                <div className="font-medium">{cm.author}</div>
                <div className="text-xs text-muted-foreground mb-1">{new Date(cm.at).toLocaleString()}</div>
                <div>{cm.body}</div>
              </div>
            ))}
          </div>
          <form onSubmit={submitComment} className="space-y-2">
            {!form.signer_name && <Input placeholder="Your name" value={form.signer_name} onChange={(e)=>setForm({...form, signer_name:e.target.value})} data-testid="comment-name" />}
            <Textarea rows={2} placeholder="Leave a comment or question" value={comment} onChange={(e)=>setComment(e.target.value)} data-testid="comment-body" />
            <div className="flex justify-end"><Button type="submit" size="sm" variant="outline" data-testid="comment-submit">Add comment</Button></div>
          </form>
        </Card>
      </div>
    </div>
  );
}
