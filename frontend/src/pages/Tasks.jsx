import { useEffect, useState } from "react";
import PageHeader from "../components/layout/PageHeader";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "../components/ui/dialog";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { api } from "../lib/apiClient";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { formatDate } from "../lib/format";

const STATUSES = ["todo", "in_progress", "review", "done"];
const STATUS_LABEL = { todo: "To do", in_progress: "In progress", review: "Review", done: "Done" };
const PRIORITY_COLOR = { low: "outline", medium: "secondary", high: "default", urgent: "destructive" };
const EMPTY = { title: "", description: "", status: "todo", priority: "medium", due_date: "" };

export default function Tasks() {
  const [tasks, setTasks] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [view, setView] = useState("kanban");

  const load = async () => {
    const { data } = await api.get("/tasks");
    setTasks(data);
  };
  useEffect(() => { load(); }, []);

  const create = async (e) => {
    e.preventDefault();
    try {
      await api.post("/tasks", form);
      toast.success("Task created"); setOpen(false); setForm(EMPTY); load();
    } catch (err) { toast.error("Failed"); }
  };

  const move = async (t, status) => { await api.patch(`/tasks/${t.id}`, { ...t, status }); load(); };
  const remove = async (id) => { await api.delete(`/tasks/${id}`); load(); };

  const byStatus = (s) => tasks.filter((t) => t.status === s);

  return (
    <>
      <PageHeader
        title="Tasks & projects"
        description="Prioritise what moves the needle. Track progress across your team."
        right={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild><Button data-testid="new-task-btn"><Plus className="h-4 w-4 mr-1" />New task</Button></DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>New task</DialogTitle></DialogHeader>
              <form onSubmit={create} className="space-y-3">
                <div className="space-y-1.5"><Label>Title</Label><Input value={form.title} onChange={(e)=>setForm({...form, title:e.target.value})} required data-testid="task-title-input" /></div>
                <div className="space-y-1.5"><Label>Description</Label><Input value={form.description} onChange={(e)=>setForm({...form, description:e.target.value})} /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5"><Label>Priority</Label>
                    <Select value={form.priority} onValueChange={(v)=>setForm({...form, priority:v})}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent><SelectItem value="low">Low</SelectItem><SelectItem value="medium">Medium</SelectItem><SelectItem value="high">High</SelectItem><SelectItem value="urgent">Urgent</SelectItem></SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5"><Label>Due date</Label><Input type="date" value={form.due_date} onChange={(e)=>setForm({...form, due_date:e.target.value})} /></div>
                </div>
                <DialogFooter><Button type="submit" data-testid="task-save-btn">Create task</Button></DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        }
      />

      <div className="p-8">
        <Tabs value={view} onValueChange={setView}>
          <TabsList data-testid="task-view-tabs"><TabsTrigger value="kanban">Kanban</TabsTrigger><TabsTrigger value="list">List</TabsTrigger></TabsList>

          <TabsContent value="kanban" className="mt-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {STATUSES.map((s) => (
                <div key={s} className="flex flex-col rounded-lg border border-border bg-card min-h-[60vh]" data-testid={`task-column-${s}`}>
                  <div className="px-4 py-3 border-b border-border">
                    <div className="text-sm font-semibold">{STATUS_LABEL[s]}</div>
                    <div className="text-xs text-muted-foreground">{byStatus(s).length} tasks</div>
                  </div>
                  <div className="flex-1 p-3 space-y-2 n-scroll overflow-y-auto">
                    {byStatus(s).map((t) => (
                      <Card key={t.id} className="p-3 n-card-hover border-border/60">
                        <div className="flex items-start justify-between gap-2">
                          <div className="font-medium text-sm">{t.title}</div>
                          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={()=>remove(t.id)}><Trash2 className="h-3 w-3" /></Button>
                        </div>
                        {t.due_date && <div className="text-xs text-muted-foreground mt-1">Due {formatDate(t.due_date)}</div>}
                        <div className="mt-2 flex items-center justify-between">
                          <Badge variant={PRIORITY_COLOR[t.priority] || "secondary"} className="text-[10px]">{t.priority}</Badge>
                          <Select value={t.status} onValueChange={(v)=>move(t, v)}>
                            <SelectTrigger className="h-7 w-[130px] text-xs"><SelectValue /></SelectTrigger>
                            <SelectContent>{STATUSES.map(x => <SelectItem key={x} value={x}>{STATUS_LABEL[x]}</SelectItem>)}</SelectContent>
                          </Select>
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="list" className="mt-6">
            <Card className="border-border/70">
              {tasks.length === 0 && <div className="p-8 text-center text-sm text-muted-foreground">No tasks yet.</div>}
              {tasks.map((t) => (
                <div key={t.id} className="flex items-center justify-between px-6 py-3 border-b border-border/60 last:border-0">
                  <div>
                    <div className="font-medium text-sm">{t.title}</div>
                    <div className="text-xs text-muted-foreground">{STATUS_LABEL[t.status]} · {t.priority}</div>
                  </div>
                  <div className="text-xs text-muted-foreground">{t.due_date ? formatDate(t.due_date) : ""}</div>
                </div>
              ))}
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}
