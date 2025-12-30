import React from 'react';
import { Link } from 'react-router-dom';
import { FaArrowRight } from 'react-icons/fa';

const ServiceCard = ({ service, onClick }) => {
  const handleClick = (e) => {
    if (service.isImageEditor && onClick) {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <div className="service-card card group overflow-hidden rounded-2xl shadow-lg">
      {/* Image header with gradient overlay */}
      <div className="relative h-40 overflow-hidden">
        {service.image ? (
          <>
            <img
              src={service.image}
              alt={service.title}
              className="w-full h-full object-cover"
            />
            <div className={`absolute inset-0 bg-gradient-to-t ${service.color} opacity-80`}></div>
          </>
        ) : (
          <div className={`h-full w-full flex items-center justify-center bg-gradient-to-r ${service.color}`}>
            <div className="text-white">
              {service.icon}
            </div>
          </div>
        )}
        <div className="absolute bottom-4 left-4 right-4">
          <h3 className="text-xl font-semibold text-white">{service.title}</h3>
        </div>
      </div>

      <div className="p-6 flex-grow flex flex-col bg-white">
        <p className="text-gray-600 mb-4 flex-grow">{service.description}</p>
        {service.isImageEditor ? (
          <button
            onClick={handleClick}
            className="inline-flex items-center text-indigo-600 font-medium hover:text-indigo-800 transition-colors"
          >
            Open Editor
            <FaArrowRight className="ml-1 text-sm group-hover:translate-x-1 transition-transform" />
          </button>
        ) : (
          <Link
            to={service.path}
            className="inline-flex items-center text-indigo-600 font-medium hover:text-indigo-800 transition-colors"
          >
            Try it
            <FaArrowRight className="ml-1 text-sm group-hover:translate-x-1 transition-transform" />
          </Link>
        )}
      </div>
    </div>
  );
};

export default ServiceCard;