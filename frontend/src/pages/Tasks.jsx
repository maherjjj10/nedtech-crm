import { useEffect, useState } from "react";
import PageHeader from "../components/layout/PageHeader";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "../components/ui/dialog";
import { Label } from "../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "../components/ui/tabs";
import { api } from "../lib/apiClient";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { formatDate } from "../lib/format";
import { useLanguage } from "../i18n";

const STATUSES = ["todo", "in_progress", "review", "done"];

const STATUS_LABEL_KEYS = {
  todo: "toDo",
  in_progress: "inProgress",
  review: "review",
  done: "done",
};

const PRIORITY_COLOR = {
  low: "outline",
  medium: "secondary",
  high: "default",
  urgent: "destructive",
};

const EMPTY = {
  title: "",
  description: "",
  status: "todo",
  priority: "medium",
  due_date: "",
};

export default function Tasks() {
  const { t } = useLanguage();

  const [tasks, setTasks] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [view, setView] = useState("kanban");

  const load = async () => {
    try {
      const { data } = await api.get("/tasks");
      setTasks(data);
    } catch {
      toast.error(t("loadFailed"));
    }
  };

  useEffect(() => {
    load();
  }, []);

  const create = async (e) => {
    e.preventDefault();

    try {
      await api.post("/tasks", form);

      toast.success(t("taskCreated"));

      setOpen(false);
      setForm(EMPTY);
      load();
    } catch {
      toast.error(t("taskCreateFailed"));
    }
  };

  const move = async (task, status) => {
    try {
      await api.patch(`/tasks/${task.id}`, {
        ...task,
        status,
      });

      load();
    } catch {
      toast.error(t("taskUpdateFailed"));
    }
  };

  const remove = async (id) => {
    try {
      await api.delete(`/tasks/${id}`);

      toast.success(t("taskDeleted"));
      load();
    } catch {
      toast.error(t("deleteFailed"));
    }
  };

  const byStatus = (status) =>
    tasks.filter((task) => task.status === status);

  return (
    <>
      <PageHeader
        title={t("tasksProjects")}
        description={t("tasksDescription")}
        right={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button
                onClick={() => {
                  setForm(EMPTY);
                  setOpen(true);
                }}
              >
                <Plus className="h-4 w-4 mr-2" />
                {t("newTask")}
              </Button>
            </DialogTrigger>

            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>{t("newTask")}</DialogTitle>
              </DialogHeader>

              <form onSubmit={create} className="space-y-4">

                <div className="space-y-2">
                  <Label>{t("title")}</Label>

                  <Input
                    value={form.title}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        title: e.target.value,
                      })
                    }
                    required
                    data-testid="task-title-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label>{t("description")}</Label>

                  <Input
                    value={form.description}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        description: e.target.value,
                      })
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label>{t("priority")}</Label>

                  <Select
                    value={form.priority}
                    onValueChange={(value) =>
                      setForm({
                        ...form,
                        priority: value,
                      })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>

                    <SelectContent>
                      <SelectItem value="low">
                        {t("low")}
                      </SelectItem>

                      <SelectItem value="medium">
                        {t("medium")}
                      </SelectItem>

                      <SelectItem value="high">
                        {t("high")}
                      </SelectItem>

                      <SelectItem value="urgent">
                        {t("urgent")}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>{t("dueDate")}</Label>

                  <Input
                    type="date"
                    value={form.due_date}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        due_date: e.target.value,
                      })
                    }
                  />
                </div>

                <DialogFooter>
                  <Button type="submit">
                    {t("createTask")}
                  </Button>
                </DialogFooter>

              </form>
            </DialogContent>
          </Dialog>
        }
      />

      <div className="p-8">

        <Tabs
          value={view}
          onValueChange={setView}
        >
          <TabsList data-testid="task-view-tabs">

            <TabsTrigger value="kanban">
              {t("kanban")}
            </TabsTrigger>

            <TabsTrigger value="list">
              {t("list")}
            </TabsTrigger>

          </TabsList>

          {/* KANBAN */}
          <TabsContent
            value="kanban"
            className="mt-6"
          >
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">

              {STATUSES.map((status) => (
                <div
                  key={status}
                  className="flex flex-col rounded-lg border border-border bg-card min-h-[60vh]"
                  data-testid={`task-column-${status}`}
                >

                  <div className="px-4 py-3 border-b border-border">

                    <div className="text-sm font-semibold">
                      {t(STATUS_LABEL_KEYS[status])}
                    </div>

                    <div className="text-xs text-muted-foreground">
                      {byStatus(status).length}{" "}
                      {t("tasksCount")}
                    </div>

                  </div>

                  <div className="flex-1 p-3 space-y-2 n-scroll overflow-y-auto">

                    {byStatus(status).map((task) => (
                      <Card
                        key={task.id}
                        className="p-3 n-card-hover border-border/60"
                      >

                        <div className="flex items-start justify-between gap-2">

                          <div className="font-medium text-sm">
                            {task.title}
                          </div>

                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() =>
                              remove(task.id)
                            }
                            title={t("delete")}
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>

                        </div>

                        {task.due_date && (
                          <div className="text-xs text-muted-foreground mt-1">
                            {t("due")}{" "}
                            {formatDate(task.due_date)}
                          </div>
                        )}

                        <div className="mt-2 flex items-center justify-between">

                          <Badge
                            variant={
                              PRIORITY_COLOR[
                                task.priority
                              ] || "secondary"
                            }
                            className="text-[10px]"
                          >
                            {t(task.priority)}
                          </Badge>

                          <Select
                            value={task.status}
                            onValueChange={(value) =>
                              move(task, value)
                            }
                          >
                            <SelectTrigger className="h-7 w-[130px] text-xs">
                              <SelectValue />
                            </SelectTrigger>

                            <SelectContent>
                              {STATUSES.map((statusOption) => (
                                <SelectItem
                                  key={statusOption}
                                  value={statusOption}
                                >
                                  {t(
                                    STATUS_LABEL_KEYS[
                                      statusOption
                                    ]
                                  )}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>

                        </div>

                      </Card>
                    ))}

                  </div>
                </div>
              ))}

            </div>
          </TabsContent>

          {/* LIST */}
          <TabsContent
            value="list"
            className="mt-6"
          >
            <Card className="border-border/70">

              {tasks.length === 0 && (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  {t("noTasksYet")}
                </div>
              )}

              {tasks.map((task) => (
                <div
                  key={task.id}
                  className="flex items-center justify-between px-6 py-3 border-b border-border/60 last:border-0"
                >

                  <div>

                    <div className="font-medium text-sm">
                      {task.title}
                    </div>

                    <div className="text-xs text-muted-foreground">
                      {t(
                        STATUS_LABEL_KEYS[
                          task.status
                        ]
                      )}{" "}
                      · {t(task.priority)}
                    </div>

                  </div>

                  <div className="text-xs text-muted-foreground">
                    {task.due_date
                      ? formatDate(task.due_date)
                      : ""}
                  </div>

                </div>
              ))}

            </Card>
          </TabsContent>

        </Tabs>
      </div>
    </>
  );
}