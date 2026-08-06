import { useEffect, useState } from "react";
import PageHeader from "../components/layout/PageHeader";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";
import { Card } from "../components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { api } from "../lib/apiClient";
import { Sparkles, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function AIAssistant() {
  const [tasks, setTasks] = useState([]);
  const [task, setTask] = useState("chat");
  const [context, setContext] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);

  useEffect(() => { api.get("/ai/tasks").then(r => setTasks(r.data)).catch(()=>{}); }, []);

  const run = async () => {
    if (!context.trim()) { toast.error("Add some context first"); return; }
    setLoading(true); setResponse("");
    try {
      const { data } = await api.post("/ai/run", { task, context, session_id: sessionId });
      setResponse(data.text); setSessionId(data.session_id);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "AI failed. Check EMERGENT_LLM_KEY.");
    } finally { setLoading(false); }
  };

  return (
    <>
      <PageHeader
        title="AI assistant"
        description="Summarise clients, draft quotes, analyse sales — powered by GPT-5.4."
      />
      <div className="p-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="p-6 border-border/70 lg:col-span-1">
            <div className="flex items-center gap-2 mb-4">
              <div className="h-8 w-8 rounded-md bg-foreground text-background flex items-center justify-center"><Sparkles className="h-4 w-4" /></div>
              <div className="font-semibold">Choose a task</div>
            </div>
            <div className="space-y-3">
              <Select value={task} onValueChange={setTask}>
                <SelectTrigger data-testid="ai-task-select"><SelectValue /></SelectTrigger>
                <SelectContent>{tasks.map(t => <SelectItem key={t.code} value={t.code}>{t.label}</SelectItem>)}</SelectContent>
              </Select>
              <Textarea
                placeholder="Paste your client notes, sales data, or context here…"
                rows={10} value={context} onChange={(e)=>setContext(e.target.value)}
                data-testid="ai-context-input"
              />
              <Button onClick={run} disabled={loading} className="w-full" data-testid="ai-run-btn">
                {loading ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Thinking…</> : <>Run assistant</>}
              </Button>
            </div>
          </Card>

          <Card className="p-6 border-border/70 lg:col-span-2 min-h-[400px]">
            <div className="n-overline mb-3">Response</div>
            {response ? (
              <div className="prose prose-sm max-w-none whitespace-pre-wrap text-sm leading-relaxed" data-testid="ai-response">{response}</div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground text-sm">
                <Sparkles className="h-8 w-8 mb-3 opacity-30" />
                Your AI-generated response will appear here.
              </div>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
