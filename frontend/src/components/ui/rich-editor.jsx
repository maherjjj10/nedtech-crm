import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import { Table } from "@tiptap/extension-table";
import { TableRow } from "@tiptap/extension-table-row";
import { TableCell } from "@tiptap/extension-table-cell";
import { TableHeader } from "@tiptap/extension-table-header";
import { Image } from "@tiptap/extension-image";
import { Link } from "@tiptap/extension-link";
import { Placeholder } from "@tiptap/extension-placeholder";
import { useEffect } from "react";
import {
  Bold, Italic, Underline as UnderlineIcon, Heading1, Heading2, Heading3,
  List, ListOrdered, Quote, Undo, Redo, Table as TableIcon, Image as ImageIcon,
  Link as LinkIcon, Minus,
} from "lucide-react";
import { Button } from "./button";
import { cn } from "../../lib/utils";

const TOOLBAR_BTN = "h-8 w-8 p-0 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground";
const TOOLBAR_ACTIVE = "bg-accent text-foreground";

export function RichEditor({ value, onChange, placeholder = "Write your contract…", editable = true, className = "" }) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      Link.configure({ openOnClick: false, HTMLAttributes: { class: "underline text-foreground" } }),
      Image,
      Table.configure({ resizable: false, HTMLAttributes: { class: "n-table" } }),
      TableRow,
      TableHeader,
      TableCell,
      Placeholder.configure({ placeholder }),
    ],
    content: value || "",
    editable,
    onUpdate: ({ editor }) => onChange?.(editor.getHTML()),
    editorProps: {
      attributes: {
        class: "prose prose-sm dark:prose-invert max-w-none min-h-[320px] px-4 py-3 focus:outline-none",
        "data-testid": "rich-editor",
      },
    },
  });

  // Keep editor in sync when parent replaces value (e.g. loading template).
  useEffect(() => {
    if (!editor) return;
    if (value !== undefined && value !== editor.getHTML()) {
      editor.commands.setContent(value || "", false);
    }
    // eslint-disable-next-line
  }, [value, editor]);

  if (!editor) return null;
  const B = ({ onClick, active, testid, title, children }) => (
    <button type="button" onClick={onClick} title={title} data-testid={testid}
      className={cn(TOOLBAR_BTN, active && TOOLBAR_ACTIVE)}>{children}</button>
  );

  const promptImage = () => {
    const url = window.prompt("Image URL (https://…)");
    if (url) editor.chain().focus().setImage({ src: url }).run();
  };
  const promptLink = () => {
    const url = window.prompt("URL", editor.getAttributes("link").href || "https://");
    if (url === null) return;
    if (url === "") editor.chain().focus().unsetLink().run();
    else editor.chain().focus().extendMarkRange("link").setLink({ href: url }).run();
  };

  return (
    <div className={cn("border border-border rounded-md bg-background", className)} data-testid="rich-editor-wrapper">
      {editable && (
        <div className="flex flex-wrap items-center gap-0.5 border-b border-border px-2 py-1.5">
          <B onClick={()=>editor.chain().focus().toggleBold().run()} active={editor.isActive("bold")} testid="rte-bold" title="Bold"><Bold className="h-4 w-4" /></B>
          <B onClick={()=>editor.chain().focus().toggleItalic().run()} active={editor.isActive("italic")} testid="rte-italic" title="Italic"><Italic className="h-4 w-4" /></B>
          <B onClick={()=>editor.chain().focus().toggleUnderline().run()} active={editor.isActive("underline")} testid="rte-underline" title="Underline"><UnderlineIcon className="h-4 w-4" /></B>
          <div className="w-px h-5 bg-border mx-1" />
          <B onClick={()=>editor.chain().focus().toggleHeading({ level: 1 }).run()} active={editor.isActive("heading",{level:1})} testid="rte-h1" title="Heading 1"><Heading1 className="h-4 w-4" /></B>
          <B onClick={()=>editor.chain().focus().toggleHeading({ level: 2 }).run()} active={editor.isActive("heading",{level:2})} testid="rte-h2" title="Heading 2"><Heading2 className="h-4 w-4" /></B>
          <B onClick={()=>editor.chain().focus().toggleHeading({ level: 3 }).run()} active={editor.isActive("heading",{level:3})} testid="rte-h3" title="Heading 3"><Heading3 className="h-4 w-4" /></B>
          <div className="w-px h-5 bg-border mx-1" />
          <B onClick={()=>editor.chain().focus().toggleBulletList().run()} active={editor.isActive("bulletList")} testid="rte-ul" title="Bullet list"><List className="h-4 w-4" /></B>
          <B onClick={()=>editor.chain().focus().toggleOrderedList().run()} active={editor.isActive("orderedList")} testid="rte-ol" title="Ordered list"><ListOrdered className="h-4 w-4" /></B>
          <B onClick={()=>editor.chain().focus().toggleBlockquote().run()} active={editor.isActive("blockquote")} testid="rte-quote" title="Quote"><Quote className="h-4 w-4" /></B>
          <B onClick={()=>editor.chain().focus().setHorizontalRule().run()} testid="rte-hr" title="Horizontal rule"><Minus className="h-4 w-4" /></B>
          <div className="w-px h-5 bg-border mx-1" />
          <B onClick={()=>editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()} testid="rte-table" title="Insert table"><TableIcon className="h-4 w-4" /></B>
          <B onClick={promptImage} testid="rte-image" title="Insert image"><ImageIcon className="h-4 w-4" /></B>
          <B onClick={promptLink} active={editor.isActive("link")} testid="rte-link" title="Link"><LinkIcon className="h-4 w-4" /></B>
          <div className="flex-1" />
          <B onClick={()=>editor.chain().focus().undo().run()} testid="rte-undo" title="Undo"><Undo className="h-4 w-4" /></B>
          <B onClick={()=>editor.chain().focus().redo().run()} testid="rte-redo" title="Redo"><Redo className="h-4 w-4" /></B>
        </div>
      )}
      <EditorContent editor={editor} />
    </div>
  );
}

/** Small variables helper — clicking a chip inserts the token at the caret. */
export const CONTRACT_VARIABLES = [
  { key: "client_name", label: "Client name" },
  { key: "company_name", label: "Company name" },
  { key: "contact_person", label: "Contact person" },
  { key: "email", label: "Email" },
  { key: "phone", label: "Phone" },
  { key: "address", label: "Address" },
  { key: "vat_number", label: "VAT number" },
  { key: "today_date", label: "Today's date" },
  { key: "start_date", label: "Start date" },
  { key: "end_date", label: "End date" },
  { key: "contract_amount", label: "Contract amount" },
  { key: "invoice_number", label: "Invoice #" },
  { key: "company_name_ours", label: "Our company" },
];
