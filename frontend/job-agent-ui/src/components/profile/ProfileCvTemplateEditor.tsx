import { Code2, Loader2, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { ApiClientError } from "../../api/client";
import {
  getProfileCvTemplate,
  saveProfileCvTemplate,
} from "../../api/profileDocumentsClient";

interface ProfileCvTemplateEditorProps {
  activeProfileId: string;
  onError: (message: string | null) => void;
}

export default function ProfileCvTemplateEditor({
  activeProfileId,
  onError,
}: ProfileCvTemplateEditorProps) {
  const [name, setName] = useState("");
  const [templateSource, setTemplateSource] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);

    void getProfileCvTemplate(activeProfileId)
      .then((template) => {
        if (!cancelled && template) {
          setName(template.name);
          setTemplateSource(template.template_source);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled && !(error instanceof ApiClientError && error.status === 404)) {
          onError(error instanceof Error ? error.message : "Failed to load CV template");
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeProfileId, onError]);

  const handleSave = async () => {
    if (!name.trim() || !templateSource.trim()) return;
    setIsSaving(true);
    onError(null);
    try {
      const saved = await saveProfileCvTemplate(activeProfileId, {
        name: name.trim(),
        template_source: templateSource.trim(),
      });
      setName(saved.name);
      setTemplateSource(saved.template_source);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Failed to save CV template");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <details className="profile-cv-template-editor">
      <summary>
        <Code2 size={14} />
        CV LaTeX template
        {isLoading ? <Loader2 size={14} className="animate-spin" /> : null}
      </summary>
      <div className="profile-cv-template-fields">
        <label>
          <span>Template name</span>
          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={isLoading || isSaving}
          />
        </label>
        <label>
          <span>LaTeX template source</span>
          <textarea
            rows={12}
            value={templateSource}
            onChange={(event) => setTemplateSource(event.target.value)}
            disabled={isLoading || isSaving}
            spellCheck={false}
          />
        </label>
        <button
          type="button"
          className="profile-cv-template-save"
          onClick={() => void handleSave()}
          disabled={isLoading || isSaving || !name.trim() || !templateSource.trim()}
        >
          {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          Save template
        </button>
      </div>
    </details>
  );
}
