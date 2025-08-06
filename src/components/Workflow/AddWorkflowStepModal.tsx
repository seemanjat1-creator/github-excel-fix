import React from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { X, Plus, Trash2, GitBranch } from 'lucide-react';
import { workflowAPI } from '../../lib/api';
import toast from 'react-hot-toast';

const schema = yup.object({
  title: yup.string().required('Title is required').min(3, 'Title must be at least 3 characters'),
  description: yup.string().required('Description is required').min(10, 'Description must be at least 10 characters'),
  step_type: yup.string().required('Step type is required'),
  is_required: yup.boolean(),
  keywords: yup.array().of(yup.string()),
  expected_response_pattern: yup.string().optional(),
  follow_up_questions: yup.array().of(yup.string()),
});

type FormData = yup.InferType<typeof schema>;

interface AddWorkflowStepModalProps {
  isOpen: boolean;
  onClose: () => void;
  workspaceId: string;
}

export const AddWorkflowStepModal: React.FC<AddWorkflowStepModalProps> = ({ 
  isOpen, 
  onClose, 
  workspaceId 
}) => {
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    control,
    watch,
  } = useForm<FormData>({
    resolver: yupResolver(schema),
    defaultValues: {
      step_type: 'question',
      is_required: true,
      keywords: [''],
      follow_up_questions: [''],
    },
  });

  const { fields: keywordFields, append: appendKeyword, remove: removeKeyword } = useFieldArray({
    control,
    name: 'keywords',
  });

  const { fields: questionFields, append: appendQuestion, remove: removeQuestion } = useFieldArray({
    control,
    name: 'follow_up_questions',
  });

  const stepType = watch('step_type');

  const createStepMutation = useMutation({
    mutationFn: (data: any) => workflowAPI.createStep({ ...data, workspace_id: workspaceId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow-steps', workspaceId] });
      toast.success('Workflow step created successfully');
      reset();
      onClose();
    },
    onError: (error: any) => {
      let errorMessage = 'Failed to create workflow step';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      toast.error(errorMessage);
    },
  });

  const onSubmit = (data: FormData) => {
    // Filter out empty keywords and questions
    const cleanedData = {
      ...data,
      title: data.title.trim(),
      description: data.description.trim(),
      keywords: data.keywords?.filter(k => k && k.trim().length > 0).map(k => k.trim()) || [],
      follow_up_questions: data.follow_up_questions?.filter(q => q && q.trim().length > 0).map(q => q.trim()) || [],
      expected_response_pattern: data.expected_response_pattern?.trim() || undefined,
    };
    
    createStepMutation.mutate(cleanedData);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
              <GitBranch className="w-4 h-4 text-white" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Add Workflow Step</h2>
          </div>
          <button
            onClick={handleClose}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-6">
          {/* Basic Information */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Step Title *
              </label>
              <input
                {...register('title')}
                type="text"
                placeholder="e.g., Ask for customer's preferred fuel type"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
              />
              {errors.title && (
                <p className="mt-1 text-sm text-red-600">{errors.title.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description *
              </label>
              <textarea
                {...register('description')}
                rows={3}
                placeholder="Describe what this step should accomplish and how the AI should handle it..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
              />
              {errors.description && (
                <p className="mt-1 text-sm text-red-600">{errors.description.message}</p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Step Type *
                </label>
                <select
                  {...register('step_type')}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                >
                  <option value="question">Question</option>
                  <option value="information">Information</option>
                  <option value="condition">Condition</option>
                  <option value="action">Action</option>
                </select>
              </div>

              <div className="flex items-center">
                <label className="flex items-center">
                  <input
                    {...register('is_required')}
                    type="checkbox"
                    className="rounded border-gray-300 text-green-600 focus:ring-green-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Required for qualification</span>
                </label>
              </div>
            </div>
          </div>

          {/* Keywords */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Keywords (AI will look for these in customer responses)
            </label>
            <div className="space-y-2">
              {keywordFields.map((field, index) => (
                <div key={field.id} className="flex items-center gap-2">
                  <input
                    {...register(`keywords.${index}` as const)}
                    type="text"
                    placeholder="e.g., petrol, gasoline, fuel"
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  />
                  {keywordFields.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeKeyword(index)}
                      className="p-2 text-red-500 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={() => appendKeyword('')}
                className="flex items-center gap-2 text-green-600 hover:text-green-700 text-sm"
              >
                <Plus className="w-4 h-4" />
                Add Keyword
              </button>
            </div>
          </div>

          {/* Expected Response Pattern */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Expected Response Pattern (Optional)
            </label>
            <input
              {...register('expected_response_pattern')}
              type="text"
              placeholder="e.g., Yes/No answer, specific product name, location"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              Help AI understand what kind of response to expect
            </p>
          </div>

          {/* Follow-up Questions */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Follow-up Questions (AI can use these if needed)
            </label>
            <div className="space-y-2">
              {questionFields.map((field, index) => (
                <div key={field.id} className="flex items-center gap-2">
                  <input
                    {...register(`follow_up_questions.${index}` as const)}
                    type="text"
                    placeholder="e.g., Could you specify which fuel type you prefer?"
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  />
                  {questionFields.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeQuestion(index)}
                      className="p-2 text-red-500 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={() => appendQuestion('')}
                className="flex items-center gap-2 text-green-600 hover:text-green-700 text-sm"
              >
                <Plus className="w-4 h-4" />
                Add Follow-up Question
              </button>
            </div>
          </div>

          {/* Step Type Info */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-blue-900 mb-2">Step Type: {stepType}</h4>
            <div className="text-xs text-blue-800">
              {stepType === 'question' && (
                <p>AI will ask questions and wait for customer responses to gather information.</p>
              )}
              {stepType === 'information' && (
                <p>AI will provide information to the customer without expecting a specific response.</p>
              )}
              {stepType === 'condition' && (
                <p>AI will check if certain conditions are met before proceeding.</p>
              )}
              {stepType === 'action' && (
                <p>AI will perform or suggest specific actions based on gathered information.</p>
              )}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createStepMutation.isPending}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md transition-colors disabled:bg-gray-400 flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              {createStepMutation.isPending ? 'Creating...' : 'Create Step'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};