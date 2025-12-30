import React, { useState } from 'react';
import { FaUser, FaBriefcase, FaGraduationCap, FaEnvelope, FaPhone, FaMapMarkerAlt, FaDownload, FaFileAlt } from 'react-icons/fa';
import toast from 'react-hot-toast';

const CvGeneratorPage = () => {
  const [cvData, setCvData] = useState({
    personal: {
      fullName: '',
      email: '',
      phone: '',
      location: '',
      summary: ''
    },
    experience: [
      { company: '', position: '', startDate: '', endDate: '', description: '' }
    ],
    education: [
      { institution: '', degree: '', startDate: '', endDate: '', description: '' }
    ],
    skills: ['']
  });

  const [generatedCv, setGeneratedCv] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleInputChange = (section, index, field, value) => {
    if (index !== undefined) {
      const updatedSection = [...cvData[section]];
      updatedSection[index][field] = value;
      setCvData({
        ...cvData,
        [section]: updatedSection
      });
    } else {
      setCvData({
        ...cvData,
        [section]: {
          ...cvData[section],
          [field]: value
        }
      });
    }
  };

  const addExperience = () => {
    setCvData({
      ...cvData,
      experience: [...cvData.experience, { company: '', position: '', startDate: '', endDate: '', description: '' }]
    });
  };

  const addEducation = () => {
    setCvData({
      ...cvData,
      education: [...cvData.education, { institution: '', degree: '', startDate: '', endDate: '', description: '' }]
    });
  };

  const addSkill = () => {
    setCvData({
      ...cvData,
      skills: [...cvData.skills, '']
    });
  };

  const removeExperience = (index) => {
    if (cvData.experience.length > 1) {
      const updated = [...cvData.experience];
      updated.splice(index, 1);
      setCvData({ ...cvData, experience: updated });
    }
  };

  const removeEducation = (index) => {
    if (cvData.education.length > 1) {
      const updated = [...cvData.education];
      updated.splice(index, 1);
      setCvData({ ...cvData, education: updated });
    }
  };

  const removeSkill = (index) => {
    if (cvData.skills.length > 1) {
      const updated = [...cvData.skills];
      updated.splice(index, 1);
      setCvData({ ...cvData, skills: updated });
    }
  };

  const handleGenerateCv = async () => {
    if (!cvData.personal.fullName || !cvData.experience[0].company) {
      toast.error('Please fill in at least your name and one experience entry');
      return;
    }

    setLoading(true);

    try {
      // Simulate AI processing
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // In a real implementation, this would be an API call to generate the CV
      // For now, we'll just set the generatedCv flag to true
      setGeneratedCv(true);
      toast.success('CV generated successfully!');
    } catch (error) {
      toast.error('Error generating CV');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    toast.success('CV downloaded successfully!');
    // In a real implementation, this would download the actual CV file
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-r from-green-500 to-teal-600 rounded-xl flex items-center justify-center mx-auto mb-4">
            <FaFileAlt className="text-white text-2xl" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">AI CV Generator</h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Create professional CVs with AI-powered content generation and smart formatting.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-6xl mx-auto">
          {/* Form */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">CV Information</h2>
            
            {/* Personal Information */}
            <div className="mb-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                <FaUser className="mr-2" /> Personal Information
              </h3>
              <div className="grid grid-cols-1 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                  <input
                    type="text"
                    value={cvData.personal.fullName}
                    onChange={(e) => handleInputChange('personal', undefined, 'fullName', e.target.value)}
                    className="input-field"
                    placeholder="John Doe"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                    <input
                      type="email"
                      value={cvData.personal.email}
                      onChange={(e) => handleInputChange('personal', undefined, 'email', e.target.value)}
                      className="input-field"
                      placeholder="john@example.com"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                    <input
                      type="tel"
                      value={cvData.personal.phone}
                      onChange={(e) => handleInputChange('personal', undefined, 'phone', e.target.value)}
                      className="input-field"
                      placeholder="+1 (555) 123-4567"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
                  <input
                    type="text"
                    value={cvData.personal.location}
                    onChange={(e) => handleInputChange('personal', undefined, 'location', e.target.value)}
                    className="input-field"
                    placeholder="City, Country"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Professional Summary</label>
                  <textarea
                    value={cvData.personal.summary}
                    onChange={(e) => handleInputChange('personal', undefined, 'summary', e.target.value)}
                    className="input-field"
                    rows="3"
                    placeholder="A brief summary of your professional background and goals..."
                  />
                </div>
              </div>
            </div>

            {/* Experience */}
            <div className="mb-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-medium text-gray-900 flex items-center">
                  <FaBriefcase className="mr-2" /> Experience
                </h3>
                <button
                  type="button"
                  onClick={addExperience}
                  className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
                >
                  + Add Experience
                </button>
              </div>
              
              {cvData.experience.map((exp, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4 mb-4">
                  <div className="grid grid-cols-2 gap-4 mb-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
                      <input
                        type="text"
                        value={exp.company}
                        onChange={(e) => handleInputChange('experience', index, 'company', e.target.value)}
                        className="input-field"
                        placeholder="Company name"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Position</label>
                      <input
                        type="text"
                        value={exp.position}
                        onChange={(e) => handleInputChange('experience', index, 'position', e.target.value)}
                        className="input-field"
                        placeholder="Job title"
                      />
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 mb-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
                      <input
                        type="month"
                        value={exp.startDate}
                        onChange={(e) => handleInputChange('experience', index, 'startDate', e.target.value)}
                        className="input-field"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
                      <input
                        type="month"
                        value={exp.endDate}
                        onChange={(e) => handleInputChange('experience', index, 'endDate', e.target.value)}
                        className="input-field"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                    <textarea
                      value={exp.description}
                      onChange={(e) => handleInputChange('experience', index, 'description', e.target.value)}
                      className="input-field"
                      rows="2"
                      placeholder="Describe your responsibilities and achievements..."
                    />
                  </div>
                  
                  {cvData.experience.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeExperience(index)}
                      className="mt-2 text-sm text-red-600 hover:text-red-800"
                    >
                      Remove Experience
                    </button>
                  )}
                </div>
              ))}
            </div>

            {/* Education */}
            <div className="mb-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-medium text-gray-900 flex items-center">
                  <FaGraduationCap className="mr-2" /> Education
                </h3>
                <button
                  type="button"
                  onClick={addEducation}
                  className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
                >
                  + Add Education
                </button>
              </div>
              
              {cvData.education.map((edu, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4 mb-4">
                  <div className="grid grid-cols-2 gap-4 mb-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Institution</label>
                      <input
                        type="text"
                        value={edu.institution}
                        onChange={(e) => handleInputChange('education', index, 'institution', e.target.value)}
                        className="input-field"
                        placeholder="University/College name"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Degree</label>
                      <input
                        type="text"
                        value={edu.degree}
                        onChange={(e) => handleInputChange('education', index, 'degree', e.target.value)}
                        className="input-field"
                        placeholder="Degree title"
                      />
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 mb-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
                      <input
                        type="month"
                        value={edu.startDate}
                        onChange={(e) => handleInputChange('education', index, 'startDate', e.target.value)}
                        className="input-field"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
                      <input
                        type="month"
                        value={edu.endDate}
                        onChange={(e) => handleInputChange('education', index, 'endDate', e.target.value)}
                        className="input-field"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                    <textarea
                      value={edu.description}
                      onChange={(e) => handleInputChange('education', index, 'description', e.target.value)}
                      className="input-field"
                      rows="2"
                      placeholder="Additional details about your education..."
                    />
                  </div>
                  
                  {cvData.education.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeEducation(index)}
                      className="mt-2 text-sm text-red-600 hover:text-red-800"
                    >
                      Remove Education
                    </button>
                  )}
                </div>
              ))}
            </div>

            {/* Skills */}
            <div className="mb-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-medium text-gray-900">Skills</h3>
                <button
                  type="button"
                  onClick={addSkill}
                  className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
                >
                  + Add Skill
                </button>
              </div>
              
              <div className="space-y-2">
                {cvData.skills.map((skill, index) => (
                  <div key={index} className="flex items-center">
                    <input
                      type="text"
                      value={skill}
                      onChange={(e) => {
                        const updated = [...cvData.skills];
                        updated[index] = e.target.value;
                        setCvData({ ...cvData, skills: updated });
                      }}
                      className="input-field flex-1"
                      placeholder="Enter a skill"
                    />
                    {cvData.skills.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeSkill(index)}
                        className="ml-2 p-2 text-red-600 hover:text-red-800"
                      >
                        <FaTrash />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={handleGenerateCv}
              disabled={loading}
              className="btn btn-primary w-full flex items-center justify-center"
            >
              {loading ? (
                <>
                  <span className="loading-spinner mr-2"></span>
                  Generating CV...
                </>
              ) : (
                'Generate Professional CV'
              )}
            </button>
          </div>

          {/* Preview */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">CV Preview</h2>
            
            {generatedCv ? (
              <div className="space-y-6">
                <div className="border rounded-lg p-6 bg-gray-50">
                  {/* Header */}
                  <div className="text-center mb-6">
                    <h1 className="text-2xl font-bold text-gray-900">{cvData.personal.fullName}</h1>
                    <p className="text-gray-600">{cvData.personal.summary}</p>
                    <div className="flex justify-center space-x-6 mt-2 text-sm text-gray-600">
                      <div className="flex items-center">
                        <FaEnvelope className="mr-1" /> {cvData.personal.email}
                      </div>
                      <div className="flex items-center">
                        <FaPhone className="mr-1" /> {cvData.personal.phone}
                      </div>
                      <div className="flex items-center">
                        <FaMapMarkerAlt className="mr-1" /> {cvData.personal.location}
                      </div>
                    </div>
                  </div>

                  {/* Experience Section */}
                  <div className="mb-6">
                    <h2 className="text-lg font-semibold text-gray-900 border-b pb-1 mb-3">Experience</h2>
                    {cvData.experience.map((exp, index) => (
                      <div key={index} className="mb-3">
                        <div className="flex justify-between">
                          <h3 className="font-medium text-gray-900">{exp.position}</h3>
                          <span className="text-gray-600">{exp.startDate} - {exp.endDate}</span>
                        </div>
                        <p className="text-gray-700 text-sm">{exp.company}</p>
                        <p className="text-gray-600 text-sm mt-1">{exp.description}</p>
                      </div>
                    ))}
                  </div>

                  {/* Education Section */}
                  <div className="mb-6">
                    <h2 className="text-lg font-semibold text-gray-900 border-b pb-1 mb-3">Education</h2>
                    {cvData.education.map((edu, index) => (
                      <div key={index} className="mb-3">
                        <div className="flex justify-between">
                          <h3 className="font-medium text-gray-900">{edu.degree}</h3>
                          <span className="text-gray-600">{edu.startDate} - {edu.endDate}</span>
                        </div>
                        <p className="text-gray-700 text-sm">{edu.institution}</p>
                        <p className="text-gray-600 text-sm mt-1">{edu.description}</p>
                      </div>
                    ))}
                  </div>

                  {/* Skills Section */}
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 border-b pb-1 mb-3">Skills</h2>
                    <div className="flex flex-wrap gap-2">
                      {cvData.skills.filter(skill => skill.trim() !== '').map((skill, index) => (
                        <span key={index} className="bg-gray-200 text-gray-800 px-3 py-1 rounded-full text-sm">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <button
                  onClick={handleDownload}
                  className="btn btn-primary w-full flex items-center justify-center"
                >
                  <FaDownload className="mr-2" /> Download CV
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-96 border-2 border-dashed border-gray-300 rounded-lg">
                <FaFileAlt className="text-gray-400 text-4xl mb-4" />
                <p className="text-gray-500 text-center">
                  Fill in your information and click "Generate Professional CV" to see your CV preview
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CvGeneratorPage;