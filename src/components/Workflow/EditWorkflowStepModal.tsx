import React, { useEffect } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { X, Save, Plus, Trash2, Edit3 } from 'lucide-react';
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

interface EditWorkflowStepModalProps {
  isOpen: boolean;
  onClose: () => void;
  step: any;
}

export const EditWorkflowStepModal: React.FC<EditWorkflowStepModalProps> = ({ 
  isOpen, 
  onClose, 
  step 
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

  // Reset form when step changes
  useEffect(() => {
    if (step) {
      reset({
        title: step.title,
        description: step.description,
        step_type: step.step_type,
        is_required: step.is_required,
        keywords: step.keywords?.length > 0 ? step.keywords : [''],
        expected_response_pattern: step.expected_response_pattern || '',
        follow_up_questions: step.follow_up_questions?.length > 0 ? step.follow_up_questions : [''],
      });
    }
  }, [step, reset]);

  const updateStepMutation = useMutation({
    mutationFn: (data: any) => workflowAPI.updateStep(step.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow-steps'] });
      toast.success('Workflow step updated successfully');
      onClose();
    },
    onError: (error: any) => {
      let errorMessage = 'Failed to update workflow step';
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
      keywords: data.keywords?.filter(k => k.trim()) || [],
      follow_up_questions: data.follow_up_questions?.filter(q => q.trim()) || [],
    };
    
    updateStepMutation.mutate(cleanedData);
  };

  if (!isOpen || !step) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
              <Edit3 className="w-4 h-4 text-white" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Edit Workflow Step</h2>
          </div>
          <button
            onClick={onClose}
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
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Required for qualification</span>
                </label>
              </div>
            </div>
          </div>

          {/* Keywords */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Keywords
            </label>
            <div className="space-y-2">
              {keywordFields.map((field, index) => (
                <div key={field.id} className="flex items-center gap-2">
                  <input
                    {...register(`keywords.${index}` as const)}
                    type="text"
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                className="flex items-center gap-2 text-blue-600 hover:text-blue-700 text-sm"
              >
                <Plus className="w-4 h-4" />
                Add Keyword
              </button>
            </div>
          </div>

          {/* Expected Response Pattern */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Expected Response Pattern
            </label>
            <input
              {...register('expected_response_pattern')}
              type="text"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Follow-up Questions */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Follow-up Questions
            </label>
            <div className="space-y-2">
              {questionFields.map((field, index) => (
                <div key={field.id} className="flex items-center gap-2">
                  <input
                    {...register(`follow_up_questions.${index}` as const)}
                    type="text"
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                className="flex items-center gap-2 text-blue-600 hover:text-blue-700 text-sm"
              >
                <Plus className="w-4 h-4" />
                Add Follow-up Question
              </button>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={updateStepMutation.isPending}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors disabled:bg-gray-400 flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              {updateStepMutation.isPending ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};