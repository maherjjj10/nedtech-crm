import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Checkbox } from "../components/ui/checkbox";
import { Badge } from "../components/ui/badge";
import {
  CheckCircle2,
  Download,
  XCircle,
  MessageSquare,
  PenLine,
  Type,
  Globe2,
  ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api/v1`;

const TEXT = {
  en: {
    contractFrom: "Contract from",
    verificationId: "Verification ID",
    preparedFor: "Prepared for",
    pdf: "PDF",
    signedBy: "Signed by",

    signContractTitle: "Sign this contract",
    fullLegalName: "Full legal name",
    emailOptional: "Email (optional)",
    signatureMethod: "Signature method",
    type: "Type",
    draw: "Draw (mouse / touch)",
    clear: "Clear",

    consentTyped:
      "I agree that typing my name and clicking Sign constitutes my legal signature and I intend to be bound by this contract.",
    consentDrawn:
      "I agree that drawing my signature and clicking Sign constitutes my legal signature and I intend to be bound by this contract.",

    signContract: "Sign contract",
    signing: "Signing…",
    reject: "Reject",

    rejectTitle: "Reject this contract",
    rejectReasonPlaceholder: "Share a reason (required)",
    rejectContract: "Reject contract",
    cancel: "Cancel",

    signedThankYou: "Signed — thank you.",
    signedDescription:
      "A copy has been recorded and shared with {company}. You can also download the PDF above.",

    contractUnavailable: "Contract unavailable",
    loading: "Loading…",

    expiredMessage:
      "This contract is {status} and can no longer be signed. Please contact {company} for a new copy.",

    comments: "Comments",
    noComments: "No comments yet.",
    yourName: "Your name",
    leaveComment: "Leave a comment or question",
    addComment: "Add comment",

    pleaseConfirmConsent: "Please confirm consent.",
    pleaseDrawSignature: "Please draw your signature.",
    pleaseShareReason: "Please share a reason.",
    enterNameComment: "Enter your name and a comment.",
    signedSuccess: "Signed — thank you.",
    rejectedSuccess: "Contract rejected.",
    failed: "Something went wrong.",
    language: "Language",

    statusDraft: "Draft",
    statusPendingReview: "Pending Review",
    statusSent: "Sent",
    statusViewed: "Viewed",
    statusSigned: "Signed",
    statusCompleted: "Completed",
    statusExpired: "Expired",
    statusCancelled: "Cancelled",
  },

  nl: {
    contractFrom: "Contract van",
    verificationId: "Verificatie-ID",
    preparedFor: "Opgesteld voor",
    pdf: "PDF",
    signedBy: "Ondertekend door",

    signContractTitle: "Dit contract ondertekenen",
    fullLegalName: "Volledige wettelijke naam",
    emailOptional: "E-mail (optioneel)",
    signatureMethod: "Handtekeningmethode",
    type: "Typen",
    draw: "Tekenen (muis / aanraken)",
    clear: "Wissen",

    consentTyped:
      "Ik ga ermee akkoord dat het typen van mijn naam en het klikken op Ondertekenen geldt als mijn wettelijke handtekening en dat ik aan dit contract gebonden ben.",
    consentDrawn:
      "Ik ga ermee akkoord dat het tekenen van mijn handtekening en het klikken op Ondertekenen geldt als mijn wettelijke handtekening en dat ik aan dit contract gebonden ben.",

    signContract: "Contract ondertekenen",
    signing: "Bezig met ondertekenen…",
    reject: "Afwijzen",

    rejectTitle: "Dit contract afwijzen",
    rejectReasonPlaceholder: "Geef een reden op (verplicht)",
    rejectContract: "Contract afwijzen",
    cancel: "Annuleren",

    signedThankYou: "Ondertekend — bedankt.",
    signedDescription:
      "Een kopie is opgeslagen en gedeeld met {company}. U kunt het PDF-bestand hierboven ook downloaden.",

    contractUnavailable: "Contract niet beschikbaar",
    loading: "Laden…",

    expiredMessage:
      "Dit contract is {status} en kan niet meer worden ondertekend. Neem contact op met {company} voor een nieuwe versie.",

    comments: "Opmerkingen",
    noComments: "Nog geen opmerkingen.",
    yourName: "Uw naam",
    leaveComment: "Laat een opmerking of vraag achter",
    addComment: "Opmerking toevoegen",

    pleaseConfirmConsent: "Bevestig uw toestemming.",
    pleaseDrawSignature: "Teken uw handtekening.",
    pleaseShareReason: "Geef een reden op.",
    enterNameComment: "Voer uw naam en een opmerking in.",
    signedSuccess: "Ondertekend — bedankt.",
    rejectedSuccess: "Contract afgewezen.",
    failed: "Er is iets misgegaan.",
    language: "Taal",

    statusDraft: "Concept",
    statusPendingReview: "In beoordeling",
    statusSent: "Verzonden",
    statusViewed: "Bekeken",
    statusSigned: "Ondertekend",
    statusCompleted: "Voltooid",
    statusExpired: "Verlopen",
    statusCancelled: "Geannuleerd",
  },

  de: {
    contractFrom: "Vertrag von",
    verificationId: "Verifizierungs-ID",
    preparedFor: "Erstellt für",
    pdf: "PDF",
    signedBy: "Unterzeichnet von",

    signContractTitle: "Diesen Vertrag unterzeichnen",
    fullLegalName: "Vollständiger rechtlicher Name",
    emailOptional: "E-Mail (optional)",
    signatureMethod: "Unterschriftsmethode",
    type: "Tippen",
    draw: "Zeichnen (Maus / Touch)",
    clear: "Löschen",

    consentTyped:
      "Ich bestätige, dass die Eingabe meines Namens und das Klicken auf „Unterzeichnen“ als meine rechtsgültige Unterschrift gilt und dass ich an diesen Vertrag gebunden bin.",
    consentDrawn:
      "Ich bestätige, dass das Zeichnen meiner Unterschrift und das Klicken auf „Unterzeichnen“ als meine rechtsgültige Unterschrift gilt und dass ich an diesen Vertrag gebunden bin.",

    signContract: "Vertrag unterzeichnen",
    signing: "Wird unterzeichnet…",
    reject: "Ablehnen",

    rejectTitle: "Diesen Vertrag ablehnen",
    rejectReasonPlaceholder: "Grund angeben (erforderlich)",
    rejectContract: "Vertrag ablehnen",
    cancel: "Abbrechen",

    signedThankYou: "Unterzeichnet — vielen Dank.",
    signedDescription:
      "Eine Kopie wurde gespeichert und mit {company} geteilt. Sie können die PDF-Datei auch oben herunterladen.",

    contractUnavailable: "Vertrag nicht verfügbar",
    loading: "Wird geladen…",

    expiredMessage:
      "Dieser Vertrag ist {status} und kann nicht mehr unterzeichnet werden. Bitte kontaktieren Sie {company}, um eine neue Version zu erhalten.",

    comments: "Kommentare",
    noComments: "Noch keine Kommentare.",
    yourName: "Ihr Name",
    leaveComment: "Kommentar oder Frage hinterlassen",
    addComment: "Kommentar hinzufügen",

    pleaseConfirmConsent: "Bitte bestätigen Sie Ihre Zustimmung.",
    pleaseDrawSignature: "Bitte zeichnen Sie Ihre Unterschrift.",
    pleaseShareReason: "Bitte geben Sie einen Grund an.",
    enterNameComment: "Geben Sie Ihren Namen und einen Kommentar ein.",
    signedSuccess: "Unterzeichnet — vielen Dank.",
    rejectedSuccess: "Vertrag abgelehnt.",
    failed: "Etwas ist schiefgelaufen.",
    language: "Sprache",

    statusDraft: "Entwurf",
    statusPendingReview: "Prüfung ausstehend",
    statusSent: "Gesendet",
    statusViewed: "Angesehen",
    statusSigned: "Unterzeichnet",
    statusCompleted: "Abgeschlossen",
    statusExpired: "Abgelaufen",
    statusCancelled: "Storniert",
  },
};

function getInitialLanguage() {
  const htmlLang = document.documentElement?.lang?.toLowerCase();

  if (htmlLang?.startsWith("nl")) return "nl";
  if (htmlLang?.startsWith("de")) return "de";

  try {
    const stored =
      localStorage.getItem("language") ||
      localStorage.getItem("ned_language") ||
      localStorage.getItem("locale");

    if (stored?.startsWith("nl")) return "nl";
    if (stored?.startsWith("de")) return "de";
  } catch {
    // Ignore storage errors.
  }

  return "en";
}

function SignaturePad({ onChange, disabled, clearLabel }) {
  const canvasRef = useRef(null);
  const drawingRef = useRef(false);

  useEffect(() => {
    const c = canvasRef.current;
    if (!c) return;

    const resize = () => {
      const ratio = window.devicePixelRatio || 1;
      const width = c.offsetWidth;
      const height = c.offsetHeight;

      c.width = width * ratio;
      c.height = height * ratio;

      const ctx = c.getContext("2d");
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      ctx.lineWidth = 2;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.strokeStyle = "#171717";
    };

    resize();
    window.addEventListener("resize", resize);

    return () => window.removeEventListener("resize", resize);
  }, []);

  const getPos = (evt) => {
    const c = canvasRef.current;
    const rect = c.getBoundingClientRect();

    const touch = evt.touches?.[0];

    const clientX = touch ? touch.clientX : evt.clientX;
    const clientY = touch ? touch.clientY : evt.clientY;

    return {
      x: clientX - rect.left,
      y: clientY - rect.top,
    };
  };

  const start = (e) => {
    if (disabled) return;

    e.preventDefault();

    drawingRef.current = true;

    const { x, y } = getPos(e);
    const ctx = canvasRef.current.getContext("2d");

    ctx.beginPath();
    ctx.moveTo(x, y);
  };

  const draw = (e) => {
    if (!drawingRef.current || disabled) return;

    e.preventDefault();

    const { x, y } = getPos(e);
    const ctx = canvasRef.current.getContext("2d");

    ctx.lineTo(x, y);
    ctx.stroke();
  };

  const end = () => {
    if (!drawingRef.current) return;

    drawingRef.current = false;

    onChange?.(canvasRef.current.toDataURL("image/png"));
  };

  const clear = () => {
    const c = canvasRef.current;
    if (!c) return;

    const ctx = c.getContext("2d");

    ctx.clearRect(0, 0, c.width, c.height);

    onChange?.(null);
  };

  return (
    <div>
      <div className="overflow-hidden rounded-xl border border-border bg-white shadow-sm">
        <canvas
          ref={canvasRef}
          onMouseDown={start}
          onMouseMove={draw}
          onMouseUp={end}
          onMouseLeave={end}
          onTouchStart={start}
          onTouchMove={draw}
          onTouchEnd={end}
          className="block h-44 w-full touch-none bg-white"
          data-testid="signature-canvas"
        />
      </div>

      <div className="mt-2 flex justify-end">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={clear}
          disabled={disabled}
          data-testid="signature-clear"
        >
          {clearLabel}
        </Button>
      </div>
    </div>
  );
}

function replaceText(text, values = {}) {
  return text.replace(/\{(\w+)\}/g, (_, key) => values[key] ?? "");
}

function statusLabel(status, lang, t) {
  const keyMap = {
    draft: "statusDraft",
    pending_review: "statusPendingReview",
    sent: "statusSent",
    viewed: "statusViewed",
    signed: "statusSigned",
    completed: "statusCompleted",
    expired: "statusExpired",
    cancelled: "statusCancelled",
  };

  return t[keyMap[status]] || status;
}

export default function PublicContract() {
  const { token } = useParams();

  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const [language, setLanguage] = useState(getInitialLanguage());

  const [form, setForm] = useState({
    signer_name: "",
    signer_email: "",
    consent: false,
    signature_type: "typed",
    signature_data: null,
  });

  const [saving, setSaving] = useState(false);
  const [signed, setSigned] = useState(false);

  const [rejecting, setRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const [comment, setComment] = useState("");
  const [comments, setComments] = useState([]);

  const t = TEXT[language] || TEXT.en;

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const refresh = () => {
    setError("");

    axios
      .get(`${API}/public/contracts/${token}`)
      .then((r) => {
        setData(r.data);
        setComments(r.data.contract.comments || []);

        if (["signed", "completed"].includes(r.data.contract.status)) {
          setSigned(true);
        }
      })
      .catch((e) => {
        setError(e?.response?.data?.detail || "Contract not found");
      });
  };

  useEffect(() => {
    refresh();
  }, [token]);

  const submitSign = async (e) => {
    e.preventDefault();

    if (!form.consent) {
      toast.error(t.pleaseConfirmConsent);
      return;
    }

    if (!form.signer_name.trim()) {
      toast.error(t.fullLegalName);
      return;
    }

    if (
      form.signature_type === "drawn" &&
      !form.signature_data
    ) {
      toast.error(t.pleaseDrawSignature);
      return;
    }

    setSaving(true);

    try {
      await axios.post(
        `${API}/public/contracts/${token}/sign`,
        form
      );

      setSigned(true);

      toast.success(t.signedSuccess);

      refresh();
    } catch (err) {
      toast.error(
        err?.response?.data?.detail || t.failed
      );
    } finally {
      setSaving(false);
    }
  };

  const submitReject = async () => {
    if (!rejectReason.trim()) {
      toast.error(t.pleaseShareReason);
      return;
    }

    try {
      await axios.post(
        `${API}/public/contracts/${token}/reject`,
        {
          signer_name: form.signer_name || "client",
          reason: rejectReason,
        }
      );

      toast.success(t.rejectedSuccess);

      setRejecting(false);
      setRejectReason("");

      refresh();
    } catch (err) {
      toast.error(
        err?.response?.data?.detail || t.failed
      );
    }
  };

  const submitComment = async (e) => {
    e.preventDefault();

    if (
      !comment.trim() ||
      !form.signer_name.trim()
    ) {
      toast.error(t.enterNameComment);
      return;
    }

    try {
      const r = await axios.post(
        `${API}/public/contracts/${token}/comment`,
        {
          author: form.signer_name,
          body: comment,
        }
      );

      setComments((current) => [
        ...current,
        r.data,
      ]);

      setComment("");
    } catch {
      toast.error(t.failed);
    }
  };

 const downloadPdf = () => {
  window.location.href = `${API}/public/contracts/${token}/pdf?lang=${language}`;
};

  const changeLanguage = (next) => {
    setLanguage(next);

    try {
      localStorage.setItem("language", next);
    } catch {
      // Ignore storage errors.
    }
  };

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-6">
        <Card className="w-full max-w-md p-8 text-center border-border/70 shadow-sm">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
            <XCircle className="h-6 w-6" />
          </div>

          <h1 className="text-xl font-bold">
            {t.contractUnavailable}
          </h1>

          <p className="mt-2 text-sm text-muted-foreground">
            {error}
          </p>
        </Card>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-sm text-muted-foreground">
          {t.loading}
        </div>
      </div>
    );
  }

  const c = data.contract;
  const tenant = data.tenant;

  const expired = c.status === "expired";
  const cancelled = c.status === "cancelled";

  const displayedStatus = statusLabel(
    c.status,
    language,
    t
  );

  return (
    <div className="min-h-screen bg-muted/30 text-foreground">
      {/* Top bar */}
      <header className="border-b border-border bg-background">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-foreground text-background font-black">
              N
            </div>

            <div className="min-w-0">
              <div className="truncate text-sm font-semibold">
                {tenant.name}
              </div>

              <div className="text-xs text-muted-foreground">
                {t.contractFrom}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="hidden sm:flex items-center gap-1 rounded-lg border border-border bg-background px-2">
              <Globe2 className="h-3.5 w-3.5 text-muted-foreground" />

              <select
                value={language}
                onChange={(e) =>
                  changeLanguage(e.target.value)
                }
                className="h-8 bg-transparent text-xs outline-none"
                aria-label={t.language}
              >
                <option value="en">English</option>
                <option value="nl">Nederlands</option>
                <option value="de">Deutsch</option>
              </select>
            </div>

            <Badge
              variant={
                signed ? "default" : "outline"
              }
              className="capitalize"
            >
              {displayedStatus}
            </Badge>

            <Button
              variant="outline"
              size="sm"
              onClick={downloadPdf}
              data-testid="pub-download-pdf"
            >
              <Download className="mr-1.5 h-4 w-4" />
              {t.pdf}
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-5 px-4 py-6 sm:px-6 sm:py-10">
        {/* Contract heading */}
        <Card className="border-border/70 bg-background shadow-sm">
          <div className="p-6 sm:p-8">
            <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                  {t.contractFrom}
                </div>

                <h1
                  className="break-words text-2xl font-bold tracking-tight sm:text-3xl"
                  data-testid="contract-title"
                >
                  {c.title}
                </h1>

                <div className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                  <span>
                    {t.verificationId}:
                  </span>

                  <span className="font-mono text-foreground">
                    {c.verification_id}
                  </span>

                  {c.client_snapshot?.company && (
                    <>
                      <span>·</span>
                      <span>
                        {t.preparedFor}{" "}
                        {c.client_snapshot.company}
                      </span>
                    </>
                  )}
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-muted-foreground" />
              </div>
            </div>

            <div
              className="contract-html mt-7 border-t border-border pt-7 text-[14.5px] leading-7"
              dangerouslySetInnerHTML={{
                __html:
                  c.rendered_html ||
                  c.body_html,
              }}
            />

            {/* Existing signature */}
            {c.signature && (
              <div className="mt-8 border-t border-border pt-5">
                <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                  {t.signedBy}
                </div>

                {c.signature.signature_type ===
                  "drawn" &&
                c.signature.signature_data ? (
                  <img
                    src={c.signature.signature_data}
                    alt="Signature"
                    className="h-16 max-w-xs object-contain"
                  />
                ) : (
                  <div className="font-serif text-2xl italic">
                    {c.signature.signer_name}
                  </div>
                )}

                <div className="mt-2 text-xs text-muted-foreground">
                  {c.signature.signer_name}
                  {" · "}
                  {new Date(
                    c.signature.signed_at
                  ).toLocaleString(
                    language === "nl"
                      ? "nl-NL"
                      : language === "de"
                      ? "de-DE"
                      : "en-US"
                  )}
                  {" · IP "}
                  {c.signature.ip || "—"}
                </div>
              </div>
            )}
          </div>
        </Card>

        {/* Sign */}
        {!signed &&
          !expired &&
          !cancelled && (
            <Card className="border-border/70 bg-background shadow-sm">
              <div className="p-6 sm:p-8">
                <div className="mb-5 flex items-center gap-2">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-foreground text-background">
                    <PenLine className="h-4 w-4" />
                  </div>

                  <div>
                    <h2 className="font-semibold">
                      {t.signContractTitle}
                    </h2>

                    <p className="text-xs text-muted-foreground">
                      {t.signatureMethod}
                    </p>
                  </div>
                </div>

                <form
                  onSubmit={submitSign}
                  className="space-y-5"
                >
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">
                        {t.fullLegalName}
                      </label>

                      <Input
                        value={form.signer_name}
                        onChange={(e) =>
                          setForm({
                            ...form,
                            signer_name:
                              e.target.value,
                          })
                        }
                        required
                        data-testid="contract-signer-input"
                        placeholder={t.fullLegalName}
                      />
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium">
                        {t.emailOptional}
                      </label>

                      <Input
                        type="email"
                        value={form.signer_email}
                        onChange={(e) =>
                          setForm({
                            ...form,
                            signer_email:
                              e.target.value,
                          })
                        }
                        data-testid="contract-signer-email"
                        placeholder="name@example.com"
                      />
                    </div>
                  </div>

                  {/* Signature method */}
                  <div>
                    <div className="mb-2 text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                      {t.signatureMethod}
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() =>
                          setForm({
                            ...form,
                            signature_type:
                              "typed",
                            signature_data:
                              null,
                          })
                        }
                        className={`flex items-center justify-center gap-2 rounded-lg border px-3 py-3 text-sm font-medium transition ${
                          form.signature_type ===
                          "typed"
                            ? "border-foreground bg-accent"
                            : "border-border hover:bg-accent/50"
                        }`}
                        data-testid="sig-type-typed"
                      >
                        <Type className="h-4 w-4" />
                        {t.type}
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          setForm({
                            ...form,
                            signature_type:
                              "drawn",
                          })
                        }
                        className={`flex items-center justify-center gap-2 rounded-lg border px-3 py-3 text-sm font-medium transition ${
                          form.signature_type ===
                          "drawn"
                            ? "border-foreground bg-accent"
                            : "border-border hover:bg-accent/50"
                        }`}
                        data-testid="sig-type-drawn"
                      >
                        <PenLine className="h-4 w-4" />
                        {t.draw}
                      </button>
                    </div>
                  </div>

                  {/* Typed signature preview */}
                  {form.signature_type ===
                    "typed" &&
                    form.signer_name && (
                      <div className="rounded-xl border border-border bg-white p-5">
                        <div className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                          {t.type}
                        </div>

                        <div className="font-serif text-3xl italic">
                          {form.signer_name}
                        </div>
                      </div>
                    )}

                  {/* Draw signature */}
                  {form.signature_type ===
                    "drawn" && (
                      <SignaturePad
                        onChange={(data) =>
                          setForm({
                            ...form,
                            signature_data:
                              data,
                          })
                        }
                        disabled={saving}
                        clearLabel={t.clear}
                      />
                    )}

                  {/* Consent */}
                  <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-border/70 bg-muted/30 p-4 text-sm leading-6">
                    <Checkbox
                      checked={form.consent}
                      onCheckedChange={(value) =>
                        setForm({
                          ...form,
                          consent: !!value,
                        })
                      }
                      data-testid="contract-consent"
                      className="mt-1"
                    />

                    <span>
                      {form.signature_type ===
                      "typed"
                        ? t.consentTyped
                        : t.consentDrawn}
                    </span>
                  </label>

                  {/* Actions */}
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <Button
                      type="submit"
                      disabled={saving}
                      className="h-11 flex-1"
                      data-testid="contract-sign-btn"
                    >
                      <CheckCircle2 className="mr-2 h-4 w-4" />

                      {saving
                        ? t.signing
                        : t.signContract}
                    </Button>

                    <Button
                      type="button"
                      variant="outline"
                      onClick={() =>
                        setRejecting(true)
                      }
                      className="h-11 sm:w-40"
                      data-testid="contract-reject-open"
                    >
                      <XCircle className="mr-2 h-4 w-4" />
                      {t.reject}
                    </Button>
                  </div>
                </form>
              </div>
            </Card>
          )}

        {/* Reject */}
        {rejecting && (
          <Card className="border-destructive/30 bg-background shadow-sm">
            <div className="p-6 sm:p-8">
              <h2 className="font-semibold">
                {t.rejectTitle}
              </h2>

              <p className="mt-1 text-xs text-muted-foreground">
                {t.pleaseShareReason}
              </p>

              <Textarea
                rows={4}
                className="mt-4"
                placeholder={
                  t.rejectReasonPlaceholder
                }
                value={rejectReason}
                onChange={(e) =>
                  setRejectReason(
                    e.target.value
                  )
                }
                data-testid="reject-reason"
              />

              <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                <Button
                  variant="destructive"
                  onClick={submitReject}
                  data-testid="reject-submit"
                >
                  <XCircle className="mr-2 h-4 w-4" />
                  {t.rejectContract}
                </Button>

                <Button
                  variant="ghost"
                  onClick={() =>
                    setRejecting(false)
                  }
                >
                  {t.cancel}
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Signed success */}
        {signed && (
          <Card className="border-border/70 bg-accent shadow-sm">
            <div className="flex items-start gap-4 p-6 sm:p-8">
              <CheckCircle2 className="mt-0.5 h-6 w-6 shrink-0" />

              <div>
                <div className="font-semibold">
                  {t.signedThankYou}
                </div>

                <div className="mt-1 text-sm text-muted-foreground">
                  {replaceText(
                    t.signedDescription,
                    {
                      company:
                        tenant.name,
                    }
                  )}
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* Expired / cancelled */}
        {(expired || cancelled) &&
          !signed && (
            <Card className="border-border/70 bg-muted/40 shadow-sm">
              <div className="p-6 text-sm">
                {replaceText(
                  t.expiredMessage,
                  {
                    status:
                      displayedStatus.toLowerCase(),
                    company: tenant.name,
                  }
                )}
              </div>
            </Card>
          )}

        {/* Comments */}
        <Card className="border-border/70 bg-background shadow-sm">
          <div className="p-6 sm:p-8">
            <div className="mb-5 flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />

              <h2 className="font-semibold">
                {t.comments}
              </h2>
            </div>

            <div className="space-y-3">
              {comments.length === 0 && (
                <div className="rounded-lg border border-dashed border-border p-5 text-center text-sm text-muted-foreground">
                  {t.noComments}
                </div>
              )}

              {comments.map((cm) => (
                <div
                  key={cm.id}
                  className="rounded-xl border border-border/70 bg-muted/20 p-4"
                >
                  <div className="font-medium text-sm">
                    {cm.author}
                  </div>

                  <div className="mt-1 text-xs text-muted-foreground">
                    {new Date(
                      cm.at
                    ).toLocaleString(
                      language === "nl"
                        ? "nl-NL"
                        : language === "de"
                        ? "de-DE"
                        : "en-US"
                    )}
                  </div>

                  <div className="mt-3 text-sm leading-6">
                    {cm.body}
                  </div>
                </div>
              ))}
            </div>

            <form
              onSubmit={submitComment}
              className="mt-5 space-y-3"
            >
              {!form.signer_name && (
                <Input
                  placeholder={t.yourName}
                  value={form.signer_name}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      signer_name:
                        e.target.value,
                    })
                  }
                  data-testid="comment-name"
                />
              )}

              <Textarea
                rows={3}
                placeholder={t.leaveComment}
                value={comment}
                onChange={(e) =>
                  setComment(e.target.value)
                }
                data-testid="comment-body"
              />

              <div className="flex justify-end">
                <Button
                  type="submit"
                  size="sm"
                  variant="outline"
                  data-testid="comment-submit"
                >
                  <MessageSquare className="mr-1.5 h-4 w-4" />
                  {t.addComment}
                </Button>
              </div>
            </form>
          </div>
        </Card>

        {/* Footer */}
        <div className="pb-6 text-center text-xs text-muted-foreground">
          {tenant.name} · Secure contract signing
        </div>
      </main>
    </div>
  );
}